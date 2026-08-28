from datetime import timedelta

import jwt
import pytest
from django.conf import settings
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from relay.audit.models import AuditLog
from relay.content.models import MediaAsset, Post
from relay.common.models import LifecycleState
from relay.approvals.models import ApprovalRequest
from relay.social.models import ChannelConnection, SocialAccount
from relay.tenancy.models import Brand, Membership, MembershipRole, Tenant


pytestmark = pytest.mark.django_db


def service_client(tenant: Tenant, brands: list[Brand], scopes: list[str]) -> APIClient:
    Membership.objects.get_or_create(
        workspace=tenant,
        subject="client:relay-test",
        defaults={"role": MembershipRole.CONTENT_CREATOR},
    )
    token = jwt.encode(
        {
            "sub": "client:relay-test",
            "workspace_id": str(tenant.id),
            "brand_ids": [str(brand.id) for brand in brands],
            "scopes": scopes,
            "iss": settings.RELAY_SERVICE_JWT_ISSUER,
            "aud": settings.RELAY_SERVICE_JWT_AUDIENCE,
            "exp": timezone.now() + timedelta(minutes=5),
        },
        settings.RELAY_SERVICE_JWT_SECRET,
        algorithm="HS256",
    )
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    return client


def test_post_creation_is_tenant_scoped_and_idempotent() -> None:
    tenant = Tenant.objects.create(slug="relay-demo", name="Relay Demo")
    brand = Brand.objects.create(workspace=tenant, slug="relay", name="Relay Brand")
    client = service_client(tenant, [brand], ["posts:write", "posts:read"])
    url = reverse("post-collection")
    payload = {"brand_id": str(brand.id), "title": "Launch", "body": "Hello from Relay"}

    created = client.post(url, payload, format="json", HTTP_IDEMPOTENCY_KEY="draft-001")
    repeated = client.post(url, payload, format="json", HTTP_IDEMPOTENCY_KEY="draft-001")
    conflict = client.post(
        url,
        {"brand_id": str(brand.id), "title": "Changed", "body": "Different"},
        format="json",
        HTTP_IDEMPOTENCY_KEY="draft-001",
    )

    assert created.status_code == 201
    assert repeated.status_code == 200
    assert repeated.data["id"] == created.data["id"]
    assert conflict.status_code == 409
    assert Post.objects.count() == 1
    assert AuditLog.objects.filter(event_type="post.draft_created").count() == 1


def test_approved_post_can_be_scheduled_idempotently() -> None:
    tenant = Tenant.objects.create(slug="scheduler", name="Scheduler")
    brand = Brand.objects.create(workspace=tenant, slug="scheduler", name="Scheduler Brand")
    client = service_client(
        tenant,
        [brand],
        ["posts:write", "posts:approve", "publications:write", "publications:read"],
    )
    post_response = client.post(
        reverse("post-collection"),
        {"brand_id": str(brand.id), "body": "Scheduled post"},
        format="json",
        HTTP_IDEMPOTENCY_KEY="draft-schedule-001",
    )
    post_id = post_response.data["id"]
    variant_id = post_response.data["default_variant_id"]
    account = SocialAccount.objects.create(
        tenant=tenant,
        brand=brand,
        provider="META",
        provider_account_id="account-1",
    )
    connection = ChannelConnection.objects.create(
        social_account=account,
        channel="META_FACEBOOK_PAGE",
        provider_channel_id="page-1",
        encrypted_access_token="not-a-real-token",
    )
    asset = MediaAsset.objects.create(
        tenant=tenant,
        brand=brand,
        storage_key="relay/test/scheduled.jpg",
        content_type="image/jpeg",
        size_bytes=42,
        upload_state=MediaAsset.UploadState.READY,
    )
    Post.objects.get(id=post_id).variants.get().media_assets.add(asset)

    approved = client.post(reverse("post-approval", kwargs={"post_id": post_id}))
    schedule_payload = {
        "post_variant_id": variant_id,
        "channel_connection_id": str(connection.id),
        "scheduled_for": (timezone.now() + timedelta(hours=1)).isoformat(),
    }
    created = client.post(
        reverse("publication-collection"),
        schedule_payload,
        format="json",
        HTTP_IDEMPOTENCY_KEY="publication-001",
    )
    repeated = client.post(
        reverse("publication-collection"),
        schedule_payload,
        format="json",
        HTTP_IDEMPOTENCY_KEY="publication-001",
    )

    assert approved.status_code == 200
    assert created.status_code == 201
    assert created.data["state"] == "SCHEDULED"
    assert repeated.status_code == 200
    assert repeated.data["id"] == created.data["id"]
    assert AuditLog.objects.filter(event_type="publication.scheduled").count() == 1


def test_post_rejects_media_from_another_brand() -> None:
    tenant = Tenant.objects.create(slug="media-owner", name="Media owner")
    brand = Brand.objects.create(workspace=tenant, slug="main", name="Main")
    other_brand = Brand.objects.create(workspace=tenant, slug="other", name="Other")
    asset = MediaAsset.objects.create(
        tenant=tenant,
        brand=other_brand,
        storage_key="relay/test/other.jpg",
        content_type="image/jpeg",
        size_bytes=10,
        upload_state=MediaAsset.UploadState.READY,
    )

    response = service_client(tenant, [brand], ["posts:write"]).post(
        reverse("post-collection"),
        {"brand_id": str(brand.id), "body": "Private media", "media_asset_ids": [str(asset.id)]},
        format="json",
        HTTP_IDEMPOTENCY_KEY="other-brand-media",
    )

    assert response.status_code == 400


def test_post_from_another_tenant_is_hidden() -> None:
    owner = Tenant.objects.create(slug="owner", name="Owner")
    outsider = Tenant.objects.create(slug="outsider", name="Outsider")
    owner_brand = Brand.objects.create(workspace=owner, slug="owner", name="Owner Brand")
    outsider_brand = Brand.objects.create(workspace=outsider, slug="outsider", name="Outsider Brand")
    post = Post.objects.create(
        tenant=owner,
        brand=owner_brand,
        title="Private",
        body="Tenant data",
        idempotency_key="owner-key",
        request_fingerprint="0" * 64,
    )

    response = service_client(outsider, [outsider_brand], ["posts:read"]).get(
        reverse("post-detail", kwargs={"post_id": post.id})
    )

    assert response.status_code == 404


def test_viewer_cannot_create_a_draft() -> None:
    tenant = Tenant.objects.create(slug="viewer", name="Viewer Workspace")
    brand = Brand.objects.create(workspace=tenant, slug="viewer", name="Viewer Brand")
    Membership.objects.create(
        workspace=tenant,
        subject="client:relay-test",
        role=MembershipRole.VIEWER,
    )
    token = jwt.encode(
        {
            "sub": "client:relay-test",
            "workspace_id": str(tenant.id),
            "brand_ids": [str(brand.id)],
            "scopes": ["posts:write"],
            "iss": settings.RELAY_SERVICE_JWT_ISSUER,
            "aud": settings.RELAY_SERVICE_JWT_AUDIENCE,
            "exp": timezone.now() + timedelta(minutes=5),
        },
        settings.RELAY_SERVICE_JWT_SECRET,
        algorithm="HS256",
    )
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    response = client.post(
        reverse("post-collection"),
        {"brand_id": str(brand.id), "body": "Not allowed"},
        format="json",
        HTTP_IDEMPOTENCY_KEY="viewer-draft",
    )

    assert response.status_code == 403


def test_client_approval_link_approves_post_without_exposing_token() -> None:
    tenant = Tenant.objects.create(slug="approvals", name="Approval Agency")
    brand = Brand.objects.create(workspace=tenant, slug="client", name="Client Brand")
    client = service_client(tenant, [brand], ["posts:write", "approvals:write"])
    created = client.post(
        reverse("post-collection"),
        {"brand_id": str(brand.id), "body": "Client review post"},
        format="json",
        HTTP_IDEMPOTENCY_KEY="approval-draft",
    )

    request_response = client.post(
        reverse("post-approval-request", kwargs={"post_id": created.data["id"]}),
        {"expires_in_days": 7},
        format="json",
    )

    assert request_response.status_code == 201
    assert "approval_url" in request_response.data
    approval_request = ApprovalRequest.objects.get(id=request_response.data["id"])
    assert approval_request.token_digest not in request_response.data["approval_url"]
    assert Post.objects.get(id=created.data["id"]).state == LifecycleState.PENDING_APPROVAL

    token = request_response.data["approval_url"].rstrip("/").rsplit("/", 1)[-1]
    public_client = APIClient()
    overview = public_client.get(reverse("approval-link", kwargs={"token": token}))
    approved = public_client.post(
        reverse("approval-link-decision", kwargs={"token": token}),
        {"decision": "APPROVED", "comment": "Looks good"},
        format="json",
    )
    replay = public_client.post(
        reverse("approval-link-decision", kwargs={"token": token}),
        {"decision": "APPROVED"},
        format="json",
    )

    assert overview.status_code == 200
    assert overview.data["post"]["body"] == "Client review post"
    assert approved.status_code == 200
    assert approved.data["decision"] == "APPROVED"
    assert replay.status_code == 409
    assert Post.objects.get(id=created.data["id"]).state == LifecycleState.APPROVED
    assert AuditLog.objects.filter(event_type="approval.approved").count() == 1


def test_client_can_request_changes_with_a_comment() -> None:
    tenant = Tenant.objects.create(slug="changes", name="Changes Agency")
    brand = Brand.objects.create(workspace=tenant, slug="changes", name="Changes Brand")
    client = service_client(tenant, [brand], ["posts:write", "approvals:write"])
    created = client.post(
        reverse("post-collection"),
        {"brand_id": str(brand.id), "body": "Needs a review"},
        format="json",
        HTTP_IDEMPOTENCY_KEY="changes-draft",
    )
    request_response = client.post(
        reverse("post-approval-request", kwargs={"post_id": created.data["id"]}),
        format="json",
    )
    token = request_response.data["approval_url"].rstrip("/").rsplit("/", 1)[-1]

    response = APIClient().post(
        reverse("approval-link-decision", kwargs={"token": token}),
        {"decision": "CHANGES_REQUESTED", "comment": "Use a warmer tone."},
        format="json",
    )

    assert response.status_code == 200
    assert response.data["decision"] == "CHANGES_REQUESTED"
    assert response.data["comments"][0]["body"] == "Use a warmer tone."
    assert Post.objects.get(id=created.data["id"]).state == LifecycleState.DRAFT


def test_workspace_member_can_revoke_client_approval_link() -> None:
    tenant = Tenant.objects.create(slug="revoke", name="Revoke Agency")
    brand = Brand.objects.create(workspace=tenant, slug="revoke", name="Revoke Brand")
    client = service_client(tenant, [brand], ["posts:write", "approvals:write"])
    created = client.post(
        reverse("post-collection"),
        {"brand_id": str(brand.id), "body": "Withdraw this review"},
        format="json",
        HTTP_IDEMPOTENCY_KEY="revoke-draft",
    )
    request_response = client.post(
        reverse("post-approval-request", kwargs={"post_id": created.data["id"]}),
        format="json",
    )
    token = request_response.data["approval_url"].rstrip("/").rsplit("/", 1)[-1]

    revoked = client.delete(
        reverse("approval-request-detail", kwargs={"approval_request_id": request_response.data["id"]})
    )
    public_response = APIClient().get(reverse("approval-link", kwargs={"token": token}))

    assert revoked.status_code == 204
    assert public_response.status_code == 404
    assert AuditLog.objects.filter(event_type="approval.revoked").count() == 1
