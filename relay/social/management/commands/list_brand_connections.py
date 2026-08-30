"""List safe identifiers needed to configure an ingestion profile."""

from django.core.management.base import BaseCommand, CommandError

from relay.social.models import ChannelConnection
from relay.tenancy.models import Brand


class Command(BaseCommand):
    help = "Lists active social channel UUIDs for one brand without exposing tokens."

    def add_arguments(self, parser):
        parser.add_argument("--workspace-slug", required=True)
        parser.add_argument("--brand-slug", required=True)

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

        connections = ChannelConnection.objects.filter(
            social_account__brand=brand, is_active=True
        ).select_related("social_account").order_by("channel", "display_name")
        if not connections.exists():
            self.stderr.write(self.style.WARNING("No active social connections were found."))
            return
        for connection in connections:
            self.stdout.write(
                f"{connection.id}\t{connection.channel}\t{connection.display_name}"
            )
