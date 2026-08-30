"""Promote already-authorized Meta channels from a test brand to a final brand."""

from django.core.management.base import BaseCommand, CommandError

from relay.audit.models import AuditLog
from relay.social.models import Channel, ChannelConnection, SocialAccount
from relay.tenancy.models import Brand, Tenant


class Command(BaseCommand):
    help = "Copies selected encrypted Meta connections between two Relay brands without re-running OAuth."

    def add_arguments(self, parser):
        parser.add_argument("--source-workspace", required=True, help="Source workspace display name.")
        parser.add_argument("--source-brand", required=True, help="Source brand display name.")
        parser.add_argument("--target-workspace-slug", required=True)
        parser.add_argument("--target-brand-slug", required=True)
        parser.add_argument(
            "--connection",
            action="append",
            required=True,
            metavar="CHANNEL:DISPLAY_NAME",
            help="Repeat for each connection, for example META_FACEBOOK_PAGE:TavisaSuite.",
        )

    def handle(self, *args, **options):
        try:
            source_workspace = Tenant.objects.get(name=options["source_workspace"], is_active=True)
            source_brand = Brand.objects.get(
                workspace=source_workspace, name=options["source_brand"], is_active=True
            )
            target_brand = Brand.objects.select_related("workspace").get(
                workspace__slug=options["target_workspace_slug"],
                slug=options["target_brand_slug"],
                workspace__is_active=True,
                is_active=True,
            )
        except (Tenant.DoesNotExist, Brand.DoesNotExist) as error:
            raise CommandError("Source or target brand was not found.") from error

        if source_brand == target_brand:
            raise CommandError("Source and target brands must be different.")

        copied = []
        for raw_connection in options["connection"]:
            try:
                channel, display_name = raw_connection.split(":", maxsplit=1)
                Channel(channel)
            except ValueError as error:
                raise CommandError(
                    "Each --connection must be CHANNEL:DISPLAY_NAME with a valid Relay channel."
                ) from error
            source = ChannelConnection.objects.select_related("social_account").filter(
                social_account__tenant=source_workspace,
                social_account__brand=source_brand,
                channel=channel,
                display_name=display_name,
                is_active=True,
            ).first()
            if source is None:
                raise CommandError(f"Active source connection was not found: {raw_connection!r}.")

            target_account, _ = SocialAccount.objects.update_or_create(
                tenant=target_brand.workspace,
                brand=target_brand,
                provider=source.social_account.provider,
                provider_account_id=source.social_account.provider_account_id,
                defaults={"display_name": source.social_account.display_name},
            )
            target, created = ChannelConnection.objects.update_or_create(
                social_account=target_account,
                channel=source.channel,
                provider_channel_id=source.provider_channel_id,
                defaults={
                    "display_name": source.display_name,
                    "encrypted_access_token": source.encrypted_access_token,
                    "token_expires_at": source.token_expires_at,
                    "granted_scopes": source.granted_scopes,
                    "is_active": source.is_active,
                },
            )
            copied.append((target, created))

        for connection, created in copied:
            AuditLog.objects.create(
                tenant=target_brand.workspace,
                brand=target_brand,
                actor_type="admin",
                actor_id="promote_meta_connections",
                event_type="meta.connection_promoted",
                subject_type="channel_connection",
                subject_id=connection.id,
                metadata={"created": created, "source_workspace": source_workspace.name},
            )
            self.stdout.write(
                self.style.SUCCESS(
                    f"{'Created' if created else 'Updated'}: {connection.id} {connection.channel} {connection.display_name}"
                )
            )
