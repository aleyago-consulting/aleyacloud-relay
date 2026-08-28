import boto3
from botocore.config import Config
from django.conf import settings


class ObjectStorageNotConfigured(Exception):
    """Relay cannot create the short-lived object URL needed for delivery."""


def b2_client():
    required = (
        settings.B2_ENDPOINT_URL,
        settings.B2_REGION,
        settings.B2_APPLICATION_KEY_ID,
        settings.B2_APPLICATION_KEY,
        settings.B2_BUCKET,
    )
    if any(not value for value in required):
        raise ObjectStorageNotConfigured("Backblaze B2 object storage is not configured.")
    return boto3.client(
        "s3",
        endpoint_url=settings.B2_ENDPOINT_URL,
        region_name=settings.B2_REGION,
        aws_access_key_id=settings.B2_APPLICATION_KEY_ID,
        aws_secret_access_key=settings.B2_APPLICATION_KEY,
        config=Config(signature_version="s3v4"),
    )


def presigned_download_url(storage_key: str) -> str:
    return b2_client().generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.B2_BUCKET, "Key": storage_key},
        ExpiresIn=settings.RELAY_MEDIA_URL_TTL_SECONDS,
    )


def presigned_upload_url(storage_key: str, content_type: str, checksum: str = "") -> str:
    """Create a short-lived, single-object browser upload URL for private B2."""
    params = {
        "Bucket": settings.B2_BUCKET,
        "Key": storage_key,
        "ContentType": content_type,
    }
    if checksum:
        params["Metadata"] = {"sha256": checksum}
    return b2_client().generate_presigned_url(
        "put_object",
        Params=params,
        ExpiresIn=settings.RELAY_MEDIA_URL_TTL_SECONDS,
    )
