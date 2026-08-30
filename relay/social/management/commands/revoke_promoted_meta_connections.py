"""Deactivate Meta connections that were previously copied between brands."""

from django.core.management.base import BaseCommand, CommandError

from relay.audit.models import AuditLog
from relay.social.models import ChannelConnection
from relay.tenancy.models import Brand


class Command(BaseCommand):
    help = (
        "Dry-runs or deactivates only connections created by the retired "
        "promote_meta_connections command. It never deletes OAuth connections."
    )

    def add_arguments(self, parser):
        parser.add_argument("--workspace-slug", required=True)
        parser.add_argument("--brand-slug", required=True)
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Apply the deactivation. Without this flag the command only reports changes.",
        )

    def handle(self, *args, **options):
        try:
            brand = Brand.objects.get(
                workspace__slug=options["workspace_slug"],
                slug=options["brand_slug"],
                workspace__is_active=True,
                is_active=True,
            )
        except Brand.DoesNotExist as error:
            raise CommandError("Active workspace/brand combination was not found.") from error

        promoted = AuditLog.objects.filter(
            tenant=brand.workspace,
            brand=brand,
            event_type="meta.connection_promoted",
            subject_type="channel_connection",
        ).values_list("subject_id", flat=True)
        connections = ChannelConnection.objects.filter(
            id__in=promoted,
            social_account__brand=brand,
            is_active=True,
        ).select_related("social_account")

        if not connections.exists():
            self.stdout.write("No copied Meta connections are active for this brand.")
            return

        for connection in connections:
            self.stdout.write(
                f"{'Deactivating' if options['apply'] else 'Would deactivate'}: "
                f"{connection.id} {connection.channel} {connection.display_name}"
            )

        if not options["apply"]:
            self.stdout.write(self.style.WARNING("Dry run only. Re-run with --apply to deactivate."))
            return

        for connection in connections:
            connection.is_active = False
            connection.save(update_fields=("is_active", "updated_at"))
            AuditLog.objects.create(
                tenant=brand.workspace,
                brand=brand,
                actor_type="admin",
                actor_id="revoke_promoted_meta_connections",
                event_type="meta.promoted_connection_revoked",
                subject_type="channel_connection",
                subject_id=connection.id,
                metadata={"reason": "retired_cross_brand_connection_copy"},
            )
        self.stdout.write(self.style.SUCCESS("Copied Meta connections have been deactivated."))
