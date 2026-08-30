from dataclasses import dataclass
from pathlib import PurePath
from uuid import uuid4

from django.conf import settings
from django.db import transaction

from relay.audit.models import AuditLog
from relay.content.models import MediaAsset
from relay.content.storage import ObjectStorageNotConfigured, b2_client, presigned_upload_url
from relay.tenancy.models import Brand, Tenant


class InvalidMediaAsset(Exception):
    """An asset cannot be attached to a post in this workspace and brand."""


class MediaUploadUnavailable(Exception):
    """Relay cannot issue or confirm a private object-store upload."""


SUPPORTED_IMAGE_TYPES = frozenset({"image/jpeg", "image/png"})
MAX_IMAGE_BYTES = 10 * 1024 * 1024
MAX_POST_IMAGES = 10


@dataclass(frozen=True)
class MediaUploadIntent:
    asset: MediaAsset
    upload_url: str


def _safe_filename(filename: str) -> str:
    name = PurePath(filename).name.strip()
    if not name:
        return "image"
    return "".join(
        character for character in name if character.isalnum() or character in ".-_"
    )[:120] or "image"


@transaction.atomic
def create_media_upload_intent(
    *,
    tenant: Tenant,
    brand: Brand,
    subject: str,
    filename: str,
    content_type: str,
    size_bytes: int,
    checksum: str = "",
) -> MediaUploadIntent:
    if content_type not in SUPPORTED_IMAGE_TYPES or not 0 < size_bytes <= MAX_IMAGE_BYTES:
        raise InvalidMediaAsset
    if checksum and (
        len(checksum) != 64 or any(char not in "0123456789abcdef" for char in checksum.lower())
    ):
        raise InvalidMediaAsset

    asset_id = uuid4()
    storage_key = (
        f"relay/workspaces/{tenant.id}/brands/{brand.id}/assets/{asset_id}/{_safe_filename(filename)}"
    )
    asset = MediaAsset.objects.create(
        id=asset_id,
        tenant=tenant,
        brand=brand,
        storage_key=storage_key,
        content_type=content_type,
        size_bytes=size_bytes,
        checksum=checksum.lower(),
    )
    try:
        upload_url = presigned_upload_url(storage_key, content_type, checksum.lower())
    except ObjectStorageNotConfigured as error:
        asset.delete()
        raise MediaUploadUnavailable from error
    AuditLog.objects.create(
        tenant=tenant,
        brand=brand,
        actor_type="service",
        actor_id=subject,
        event_type="media.upload_intent_created",
        subject_type="media_asset",
        subject_id=asset.id,
        metadata={"content_type": content_type, "size_bytes": size_bytes},
    )
    return MediaUploadIntent(asset=asset, upload_url=upload_url)


@transaction.atomic
def confirm_media_upload(*, asset: MediaAsset, tenant: Tenant, subject: str) -> MediaAsset:
    asset = MediaAsset.objects.select_for_update().get(id=asset.id, tenant=tenant)
    if asset.upload_state == MediaAsset.UploadState.READY:
        return asset
    if asset.upload_state != MediaAsset.UploadState.PENDING:
        raise InvalidMediaAsset
    try:
        object_metadata = b2_client().head_object(Bucket=settings.B2_BUCKET, Key=asset.storage_key)
    except Exception as error:
        raise MediaUploadUnavailable from error

    remote_size = object_metadata.get("ContentLength")
    remote_type = object_metadata.get("ContentType", "").split(";", 1)[0].lower()
    if remote_size != asset.size_bytes or remote_type != asset.content_type:
        asset.upload_state = MediaAsset.UploadState.FAILED
        asset.save(update_fields=("upload_state", "updated_at"))
        raise InvalidMediaAsset
    if asset.checksum:
        remote_checksum = object_metadata.get("Metadata", {}).get("sha256", "").lower()
        if remote_checksum and remote_checksum != asset.checksum:
            asset.upload_state = MediaAsset.UploadState.FAILED
            asset.save(update_fields=("upload_state", "updated_at"))
            raise InvalidMediaAsset

    asset.upload_state = MediaAsset.UploadState.READY
    asset.save(update_fields=("upload_state", "updated_at"))
    AuditLog.objects.create(
        tenant=tenant,
        brand=asset.brand,
        actor_type="service",
        actor_id=subject,
        event_type="media.upload_confirmed",
        subject_type="media_asset",
        subject_id=asset.id,
        metadata={"content_type": asset.content_type, "size_bytes": asset.size_bytes},
    )
    return asset


def ready_assets_for_post(*, tenant: Tenant, brand: Brand, asset_ids: list[object]) -> list[MediaAsset]:
    normalized_ids = list(dict.fromkeys(asset_ids))
    if len(normalized_ids) > MAX_POST_IMAGES:
        raise InvalidMediaAsset
    assets = list(
        MediaAsset.objects.select_for_update().filter(
            id__in=normalized_ids,
            tenant=tenant,
            brand=brand,
            upload_state=MediaAsset.UploadState.READY,
        )
    )
    if len(assets) != len(normalized_ids):
        raise InvalidMediaAsset
    # Preserve the order selected by the author: it is the slide order of a carousel.
    assets_by_id = {asset.id: asset for asset in assets}
    return [assets_by_id[asset_id] for asset_id in normalized_ids]


def ordered_media_assets(*, variant) -> list[MediaAsset]:
    """Return a variant's images in the author-selected carousel order.

    Variants created before carousel support have no stored order; retaining their
    creation order keeps existing single-image posts fully backward-compatible.
    """
    assets = list(variant.media_assets.all().order_by("created_at", "id"))
    assets_by_id = {str(asset.id): asset for asset in assets}
    ordered = [
        assets_by_id[asset_id]
        for asset_id in variant.media_asset_order
        if asset_id in assets_by_id
    ]
    selected = {asset.id for asset in ordered}
    return ordered + [asset for asset in assets if asset.id not in selected]
