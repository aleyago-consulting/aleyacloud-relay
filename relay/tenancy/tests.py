import pytest
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
