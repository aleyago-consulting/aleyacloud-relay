"""Provision an isolated workspace and brands for draft ingestion."""

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from relay.api.authentication import panel_subject
from relay.tenancy.models import Brand, Membership, MembershipRole, Tenant


class Command(BaseCommand):
    help = "Creates or updates a content workspace and its brands without connecting social accounts."

    def add_arguments(self, parser):
        parser.add_argument("--workspace-slug", required=True)
        parser.add_argument("--workspace-name", required=True)
        parser.add_argument(
            "--brand",
            action="append",
            required=True,
            metavar="SLUG:NAME",
            help="Repeat once per brand, for example --brand tavisasuite:TavisaSuite.",
        )
        parser.add_argument(
            "--owner-username",
            help="Optional existing Django user to grant OWNER access to the workspace.",
        )

    def handle(self, *args, **options):
        workspace, workspace_created = Tenant.objects.update_or_create(
            slug=options["workspace_slug"],
            defaults={"name": options["workspace_name"], "is_active": True},
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Workspace {'created' if workspace_created else 'updated'}: {workspace.slug} ({workspace.id})"
            )
        )

        for raw_brand in options["brand"]:
            try:
                slug, name = raw_brand.split(":", maxsplit=1)
            except ValueError as error:
                raise CommandError("Each --brand value must have the form SLUG:NAME.") from error
            slug, name = slug.strip(), name.strip()
            if not slug or not name:
                raise CommandError("Each --brand value must have a non-empty slug and name.")
            brand, created = Brand.objects.update_or_create(
                workspace=workspace,
                slug=slug,
                defaults={"name": name, "is_active": True},
            )
            self.stdout.write(
                self.style.SUCCESS(
                    f"Brand {'created' if created else 'updated'}: {brand.slug} ({brand.id})"
                )
            )

        username = options.get("owner_username")
        if username:
            try:
                user = get_user_model().objects.get(username=username)
            except get_user_model().DoesNotExist as error:
                raise CommandError(f"Django user {username!r} does not exist.") from error
            membership, created = Membership.objects.update_or_create(
                workspace=workspace,
                subject=panel_subject(user.id),
                defaults={"role": MembershipRole.OWNER, "is_active": True},
            )
            self.stdout.write(
                self.style.SUCCESS(
                    f"Owner {'created' if created else 'updated'}: {user.get_username()} ({membership.id})"
                )
            )
