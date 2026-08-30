import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.db import IntegrityError

from relay.tenancy.models import Brand, Membership, MembershipRole, Tenant


pytestmark = pytest.mark.django_db


def test_brand_is_unique_within_its_workspace_only() -> None:
    first = Tenant.objects.create(slug="agency-one", name="Agency One")
    second = Tenant.objects.create(slug="agency-two", name="Agency Two")

    Brand.objects.create(workspace=first, slug="acme", name="Acme")
    Brand.objects.create(workspace=second, slug="acme", name="Acme Other")

    with pytest.raises(IntegrityError):
        Brand.objects.create(workspace=first, slug="acme", name="Duplicate")


def test_membership_is_unique_per_workspace_and_subject() -> None:
    workspace = Tenant.objects.create(slug="agency", name="Agency")
    Membership.objects.create(
        workspace=workspace,
        subject="user:creator",
        role=MembershipRole.CONTENT_CREATOR,
    )

    with pytest.raises(IntegrityError):
        Membership.objects.create(
            workspace=workspace,
            subject="user:creator",
            role=MembershipRole.VIEWER,
        )


def test_content_workspace_command_creates_brands_and_owner() -> None:
    user = get_user_model().objects.create_user(username="jorge.llavata", password="not-a-real-password")

    call_command(
        "provision_content_workspace",
        "--workspace-slug",
        "aleya-content",
        "--workspace-name",
        "Alya Content",
        "--brand",
        "tavisasuite:TavisaSuite",
        "--brand",
        "goclinicals:GoClinicals",
        "--owner-username",
        user.username,
    )

    workspace = Tenant.objects.get(slug="aleya-content")
    assert set(workspace.brands.values_list("slug", flat=True)) == {"tavisasuite", "goclinicals"}
    assert Membership.objects.get(workspace=workspace, subject=f"user:{user.id}").role == MembershipRole.OWNER
