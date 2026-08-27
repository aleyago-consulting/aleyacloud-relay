from urllib.parse import quote

from django.conf import settings

from relay.content.models import MediaAsset
from relay.content.storage import ObjectStorageNotConfigured, presigned_download_url


class MediaDeliveryUnavailable(Exception):
    """No controlled URL can be given to a social provider for this asset."""


def publishable_image_url(asset: MediaAsset) -> str:
    """Return the Relay-controlled URL used by Meta to fetch one image.

    Production must point this base URL at a short-lived, access-controlled media
    delivery endpoint; object-store keys are never exposed directly by this code.
    """
    try:
        return presigned_download_url(asset.storage_key)
    except ObjectStorageNotConfigured:
        # Compatibility for local tests only; production must use B2.
        base_url = settings.RELAY_MEDIA_PUBLIC_BASE_URL.rstrip("/")
        if base_url:
            return f"{base_url}/{quote(asset.storage_key, safe='/')}"
        raise MediaDeliveryUnavailable("Media delivery is not configured.") from None
