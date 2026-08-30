from rest_framework import serializers
from django.utils import timezone

from relay.content.models import MediaAsset, Post
from relay.content.services import ordered_media_assets
from relay.publications.models import Publication
from relay.approvals.models import ApprovalComment, ApprovalRequest
from relay.social.models import ChannelConnection


class PostCreateSerializer(serializers.Serializer):
    brand_id = serializers.UUIDField()
    title = serializers.CharField(max_length=255, required=False, allow_blank=True)
    body = serializers.CharField(allow_blank=False, trim_whitespace=False)
    media_asset_ids = serializers.ListField(
        child=serializers.UUIDField(), required=False, default=list, max_length=10
    )


class MediaUploadIntentSerializer(serializers.Serializer):
    brand_id = serializers.UUIDField()
    filename = serializers.CharField(max_length=255)
    content_type = serializers.ChoiceField(choices=("image/jpeg", "image/png"))
    size_bytes = serializers.IntegerField(min_value=1, max_value=10 * 1024 * 1024)
    checksum = serializers.RegexField(
        r"^[a-fA-F0-9]{64}$", required=False, allow_blank=True, max_length=64
    )


class MediaAssetSerializer(serializers.ModelSerializer):
    class Meta:
        model = MediaAsset
        fields = (
            "id",
            "brand_id",
            "content_type",
            "size_bytes",
            "checksum",
            "upload_state",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class ChannelConnectionSerializer(serializers.ModelSerializer):
    provider = serializers.CharField(source="social_account.provider", read_only=True)
    brand_id = serializers.UUIDField(source="social_account.brand_id", read_only=True)

    class Meta:
        model = ChannelConnection
        fields = (
            "id",
            "brand_id",
            "provider",
            "channel",
            "provider_channel_id",
            "display_name",
            "token_expires_at",
            "granted_scopes",
            "is_active",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class PostSerializer(serializers.ModelSerializer):
    default_variant_id = serializers.SerializerMethodField()
    media_asset_ids = serializers.SerializerMethodField()

    def get_default_variant_id(self, post):
        variant = post.variants.order_by("created_at").first()
        return str(variant.id) if variant else None

    def get_media_asset_ids(self, post):
        variant = post.variants.order_by("created_at").first()
        return [str(asset.id) for asset in ordered_media_assets(variant=variant)] if variant else []

    class Meta:
        model = Post
        fields = (
            "id",
            "title",
            "body",
            "state",
            "default_variant_id",
            "media_asset_ids",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class PublicationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Publication
        fields = (
            "id",
            "post_variant_id",
            "channel_connection_id",
            "scheduled_for",
            "state",
            "provider_publication_id",
            "last_error_code",
            "last_error_message",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class PublicationCreateSerializer(serializers.Serializer):
    post_variant_id = serializers.UUIDField()
    channel_connection_id = serializers.UUIDField()
    scheduled_for = serializers.DateTimeField()

    def validate_scheduled_for(self, value):
        if value <= timezone.now():
            raise serializers.ValidationError("The scheduled time must be in the future.")
        return value


class ApprovalRequestCreateSerializer(serializers.Serializer):
    expires_in_days = serializers.IntegerField(default=7, min_value=1, max_value=30)


class ApprovalDecisionSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(choices=("APPROVED", "CHANGES_REQUESTED"))
    comment = serializers.CharField(required=False, allow_blank=True, trim_whitespace=True)
    author_label = serializers.CharField(required=False, allow_blank=True, max_length=255)

    def validate(self, attrs):
        if attrs["decision"] == "CHANGES_REQUESTED" and not attrs.get("comment"):
            raise serializers.ValidationError({"comment": "This field is required when changes are requested."})
        return attrs


class ApprovalCommentSerializer(serializers.ModelSerializer):
    class Meta:
        model = ApprovalComment
        fields = ("author_label", "body", "created_at")
        read_only_fields = fields


class ApprovalRequestSerializer(serializers.ModelSerializer):
    comments = ApprovalCommentSerializer(many=True, read_only=True)
    post_id = serializers.UUIDField(read_only=True)

    class Meta:
        model = ApprovalRequest
        fields = (
            "id",
            "post_id",
            "expires_at",
            "decision",
            "decided_at",
            "comments",
        )
        read_only_fields = fields
