from unittest.mock import Mock, patch

import pytest

from relay.content.models import MediaAsset
from relay.content.services import confirm_media_upload, create_media_upload_intent
from relay.tenancy.models import Brand, Tenant


pytestmark = pytest.mark.django_db


@patch("relay.content.services.presigned_upload_url", return_value="https://b2.example.test/signed-put")
def test_upload_intent_uses_an_opaque_tenant_scoped_key(_: Mock) -> None:
    tenant = Tenant.objects.create(slug="upload", name="Upload")
    brand = Brand.objects.create(workspace=tenant, slug="brand", name="Brand")

    intent = create_media_upload_intent(
        tenant=tenant,
        brand=brand,
        subject="client:test",
        filename="../../summer image.jpg",
        content_type="image/jpeg",
        size_bytes=123,
    )

    assert intent.upload_url == "https://b2.example.test/signed-put"
    assert intent.asset.upload_state == MediaAsset.UploadState.PENDING
    assert str(tenant.id) in intent.asset.storage_key
    assert ".." not in intent.asset.storage_key


@patch("relay.content.services.b2_client")
def test_confirmed_upload_becomes_ready(mock_b2_client: Mock) -> None:
    tenant = Tenant.objects.create(slug="confirm", name="Confirm")
    brand = Brand.objects.create(workspace=tenant, slug="brand", name="Brand")
    asset = MediaAsset.objects.create(
        tenant=tenant,
        brand=brand,
        storage_key="relay/test/confirm.jpg",
        content_type="image/jpeg",
        size_bytes=123,
    )
    mock_b2_client.return_value.head_object.return_value = {
        "ContentLength": 123,
        "ContentType": "image/jpeg",
    }

    confirmed = confirm_media_upload(asset=asset, tenant=tenant, subject="client:test")

    assert confirmed.upload_state == MediaAsset.UploadState.READY
