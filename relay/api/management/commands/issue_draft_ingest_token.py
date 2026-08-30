"""Issue a least-privilege, short-lived credential for content ingestion."""

from datetime import timedelta
from uuid import uuid4

import jwt
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from relay.tenancy.models import Brand, Membership, MembershipRole


class Command(BaseCommand):
    help = "Issues a scoped JWT for one brand: draft ingestion or approved scheduling."

    def add_arguments(self, parser):
        parser.add_argument("--workspace-slug", required=True)
        parser.add_argument("--brand-slug", required=True)
        parser.add_argument(
            "--subject",
            required=True,
            help="Stable non-human identifier, for example task:content-ingest-tavisasuite.",
        )
        parser.add_argument(
            "--days",
            type=int,
            default=14,
            help="Credential lifetime in days (1-30; default 14).",
        )
        parser.add_argument(
            "--purpose",
            choices=("draft", "schedule"),
            default="draft",
            help=(
                "draft only creates DRAFT posts; schedule may also approve and schedule "
                "its own content."
            ),
        )

    def handle(self, *args, **options):
        days = options["days"]
        if not 1 <= days <= 30:
            raise CommandError("--days must be between 1 and 30.")

        try:
            brand = Brand.objects.select_related("workspace").get(
                workspace__slug=options["workspace_slug"],
                slug=options["brand_slug"],
                workspace__is_active=True,
                is_active=True,
            )
        except Brand.DoesNotExist as error:
            raise CommandError("Active workspace/brand combination was not found.") from error

        membership, created = Membership.objects.get_or_create(
            workspace=brand.workspace,
            subject=options["subject"],
            defaults={"role": MembershipRole.CONTENT_CREATOR, "is_active": True},
        )
        if not created and membership.role != MembershipRole.CONTENT_CREATOR:
            raise CommandError(
                "The supplied subject already belongs to this workspace with a different role. "
                "Use a dedicated task: subject."
            )
        if not membership.is_active:
            membership.is_active = True
            membership.save(update_fields=("is_active", "updated_at"))

        issued_at = timezone.now()
        scopes = ["media:write", "posts:write"]
        if options["purpose"] == "schedule":
            scopes.extend(("posts:approve", "publications:write"))

        token = jwt.encode(
            {
                "sub": options["subject"],
                "workspace_id": str(brand.workspace_id),
                "brand_ids": [str(brand.id)],
                "scopes": scopes,
                "iss": settings.RELAY_SERVICE_JWT_ISSUER,
                "aud": settings.RELAY_SERVICE_JWT_AUDIENCE,
                "iat": issued_at,
                "exp": issued_at + timedelta(days=days),
                "jti": str(uuid4()),
            },
            settings.RELAY_SERVICE_JWT_SECRET,
            algorithm="HS256",
        )
        self.stdout.write(token)
        capability = (
            "upload media, create drafts, approve them, and schedule publications"
            if options["purpose"] == "schedule"
            else "upload media and create drafts"
        )
        self.stderr.write(
            self.style.WARNING(
                f"Store this bearer token only in the task's secret store. It can {capability}, "
                "but cannot publish directly, read connections, or access another brand."
            )
        )
