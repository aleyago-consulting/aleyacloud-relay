import hashlib
import secrets
from dataclasses import dataclass
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from relay.approvals.models import ApprovalComment, ApprovalDecision, ApprovalRequest
from relay.audit.models import AuditLog
from relay.common.models import LifecycleState
from relay.content.models import Post
from relay.tenancy.models import Brand, Tenant


class InvalidApprovalLink(Exception):
    """The supplied approval link is expired, revoked or unknown."""


class ApprovalAlreadyDecided(Exception):
    """A client tried to submit another decision for the same link."""


class ApprovalAlreadyRevoked(Exception):
    """A workspace member tried to revoke an inactive link."""


class InvalidApprovalState(Exception):
    """The post cannot enter or leave the client-approval workflow."""


@dataclass(frozen=True)
class ApprovalLink:
    request: ApprovalRequest
    url: str


def _digest(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def _approval_url(raw_token: str) -> str:
    return f"{settings.RELAY_PUBLIC_API_URL.rstrip('/')}/approval-links/{raw_token}/"


@transaction.atomic
def request_approval(
    *, tenant: Tenant, brand: Brand, post: Post, subject: str, expires_in_days: int
) -> ApprovalLink:
    post = Post.objects.select_for_update().get(id=post.id, tenant=tenant, brand=brand)
    if post.state not in {LifecycleState.DRAFT, LifecycleState.PENDING_APPROVAL}:
        raise InvalidApprovalState

    raw_token = secrets.token_urlsafe(48)
    approval_request = ApprovalRequest.objects.create(
        brand=brand,
        post=post,
        requested_by_subject=subject,
        token_digest=_digest(raw_token),
        expires_at=timezone.now() + timedelta(days=expires_in_days),
    )
    if post.state != LifecycleState.PENDING_APPROVAL:
        post.state = LifecycleState.PENDING_APPROVAL
        post.save(update_fields=("state", "updated_at"))
    AuditLog.objects.create(
        tenant=tenant,
        brand=brand,
        actor_type="service",
        actor_id=subject,
        event_type="approval.requested",
        subject_type="approval_request",
        subject_id=approval_request.id,
        metadata={"post_id": str(post.id), "expires_at": approval_request.expires_at.isoformat()},
    )
    return ApprovalLink(request=approval_request, url=_approval_url(raw_token))


def get_active_approval_request(raw_token: str) -> ApprovalRequest:
    approval_request = ApprovalRequest.objects.select_related("post", "brand").filter(
        token_digest=_digest(raw_token)
    ).first()
    if (
        approval_request is None
        or approval_request.revoked_at is not None
        or approval_request.expires_at <= timezone.now()
    ):
        raise InvalidApprovalLink
    return approval_request


@transaction.atomic
def revoke_approval(*, approval_request: ApprovalRequest, tenant: Tenant, subject: str) -> ApprovalRequest:
    approval_request = (
        ApprovalRequest.objects.select_for_update()
        .select_related("brand", "post")
        .get(id=approval_request.id, brand__workspace=tenant)
    )
    if approval_request.revoked_at is not None or approval_request.decision != ApprovalDecision.PENDING:
        raise ApprovalAlreadyRevoked
    approval_request.revoked_at = timezone.now()
    approval_request.save(update_fields=("revoked_at", "updated_at"))
    AuditLog.objects.create(
        tenant=tenant,
        brand=approval_request.brand,
        actor_type="service",
        actor_id=subject,
        event_type="approval.revoked",
        subject_type="approval_request",
        subject_id=approval_request.id,
        metadata={"post_id": str(approval_request.post_id)},
    )
    return approval_request


@transaction.atomic
def decide_approval(
    *, raw_token: str, decision: str, comment: str = "", author_label: str = ""
) -> ApprovalRequest:
    approval_request = (
        ApprovalRequest.objects.select_for_update()
        .select_related("post", "brand", "brand__workspace")
        .filter(token_digest=_digest(raw_token))
        .first()
    )
    if (
        approval_request is None
        or approval_request.revoked_at is not None
        or approval_request.expires_at <= timezone.now()
    ):
        raise InvalidApprovalLink
    if approval_request.decision != ApprovalDecision.PENDING:
        raise ApprovalAlreadyDecided
    if decision not in {ApprovalDecision.APPROVED, ApprovalDecision.CHANGES_REQUESTED}:
        raise ValueError("Unsupported approval decision")
    if decision == ApprovalDecision.CHANGES_REQUESTED and not comment:
        raise ValueError("A comment is required when changes are requested")

    post = approval_request.post
    if post.state != LifecycleState.PENDING_APPROVAL:
        raise InvalidApprovalState
    approval_request.decision = decision
    approval_request.decided_at = timezone.now()
    approval_request.save(update_fields=("decision", "decided_at", "updated_at"))
    post.state = (
        LifecycleState.APPROVED
        if decision == ApprovalDecision.APPROVED
        else LifecycleState.DRAFT
    )
    post.save(update_fields=("state", "updated_at"))
    if comment:
        ApprovalComment.objects.create(
            approval_request=approval_request, author_label=author_label, body=comment
        )
    AuditLog.objects.create(
        tenant=approval_request.brand.workspace,
        brand=approval_request.brand,
        actor_type="approval_link",
        actor_id=str(approval_request.id),
        event_type=(
            "approval.approved"
            if decision == ApprovalDecision.APPROVED
            else "approval.changes_requested"
        ),
        subject_type="post",
        subject_id=post.id,
        metadata={"approval_request_id": str(approval_request.id)},
    )
    return approval_request
