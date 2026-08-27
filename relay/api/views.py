from django.shortcuts import get_object_or_404
from uuid import UUID
from rest_framework import status
from rest_framework import exceptions
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from relay.api.permissions import HasRelayScope
from relay.api.serializers import (
    ApprovalDecisionSerializer,
    ApprovalRequestCreateSerializer,
    ApprovalRequestSerializer,
    PostCreateSerializer,
    PostSerializer,
    PublicationCreateSerializer,
    PublicationSerializer,
)
from relay.approvals.models import ApprovalRequest
from relay.approvals.services import (
    ApprovalAlreadyRevoked,
    ApprovalAlreadyDecided,
    InvalidApprovalLink,
    InvalidApprovalState,
    decide_approval,
    get_active_approval_request,
    request_approval,
    revoke_approval,
)
from relay.api.services import (
    IdempotencyConflict,
    InvalidSchedule,
    InvalidStateTransition,
    approve_post,
    create_post_draft,
    schedule_publication,
)
from relay.content.models import Post, PostVariant
from relay.publications.models import Publication
from relay.social.models import ChannelConnection
from relay.social.crypto import TokenEncryptionError
from relay.social.meta import MetaConfigurationError, MetaProviderError
from relay.social.services import InvalidOAuthState, complete_meta_oauth, start_meta_oauth
from relay.tenancy.models import Brand, Tenant


class IdempotencyConflictResponse(exceptions.APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = "This key has already been used with different content."
    default_code = "idempotency_conflict"


class InvalidStateResponse(exceptions.APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = "The requested operation is not valid for the current resource state."
    default_code = "invalid_state"


class MetaConnectionResponse(exceptions.APIException):
    status_code = status.HTTP_502_BAD_GATEWAY
    default_detail = "Meta could not complete the connection request."
    default_code = "meta_connection_error"


class MetaConfigurationResponse(exceptions.APIException):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_detail = "Meta OAuth is not configured."
    default_code = "meta_not_configured"


class InvalidApprovalResponse(exceptions.APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = "The requested approval operation is not valid for the current resource state."
    default_code = "invalid_approval_state"


class TenantScopedAPIView(APIView):
    permission_classes = [HasRelayScope]

    def get_tenant(self):
        return get_object_or_404(Tenant, id=self.request.user.workspace_id, is_active=True)

    def get_brand(self, brand_id):
        try:
            brand_id = UUID(str(brand_id))
        except ValueError as error:
            raise exceptions.NotFound() from error
        if brand_id not in self.request.user.brand_ids:
            raise exceptions.NotFound()
        return get_object_or_404(Brand, id=brand_id, workspace=self.get_tenant(), is_active=True)


class PostCollectionView(TenantScopedAPIView):
    required_scope = "posts:write"
    required_roles = ("OWNER", "MANAGER", "CONTENT_CREATOR")

    def post(self, request):
        idempotency_key = request.headers.get("Idempotency-Key")
        if not idempotency_key or len(idempotency_key) > 255:
            raise ValidationError({"Idempotency-Key": "This header is required and has a maximum of 255 characters."})

        serializer = PostCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        brand = self.get_brand(serializer.validated_data["brand_id"])
        try:
            result = create_post_draft(
                tenant=self.get_tenant(),
                brand=brand,
                subject=request.user.subject,
                idempotency_key=idempotency_key,
                payload=serializer.validated_data,
            )
        except IdempotencyConflict as error:
            raise IdempotencyConflictResponse from error

        response_status = status.HTTP_201_CREATED if result.created else status.HTTP_200_OK
        return Response(PostSerializer(result.post).data, status=response_status)


class PostDetailView(TenantScopedAPIView):
    required_scope = "posts:read"
    required_roles = ("OWNER", "MANAGER", "CONTENT_CREATOR", "CLIENT_APPROVER", "VIEWER")

    def get(self, request, post_id):
        post = get_object_or_404(
            Post, id=post_id, tenant=self.get_tenant(), brand_id__in=self.request.user.brand_ids
        )
        return Response(PostSerializer(post).data)


class PostApprovalView(TenantScopedAPIView):
    required_scope = "posts:approve"
    required_roles = ("OWNER", "MANAGER", "CONTENT_CREATOR")

    def post(self, request, post_id):
        post = get_object_or_404(
            Post, id=post_id, tenant=self.get_tenant(), brand_id__in=self.request.user.brand_ids
        )
        try:
            post = approve_post(
                post=post,
                tenant=self.get_tenant(),
                brand=self.get_brand(post.brand_id),
                subject=request.user.subject,
            )
        except InvalidStateTransition as error:
            raise InvalidStateResponse from error
        return Response(PostSerializer(post).data)


class PostApprovalRequestView(TenantScopedAPIView):
    required_scope = "approvals:write"
    required_roles = ("OWNER", "MANAGER", "CONTENT_CREATOR")

    def post(self, request, post_id):
        post = get_object_or_404(
            Post, id=post_id, tenant=self.get_tenant(), brand_id__in=request.user.brand_ids
        )
        serializer = ApprovalRequestCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            approval_link = request_approval(
                tenant=self.get_tenant(),
                brand=self.get_brand(post.brand_id),
                post=post,
                subject=request.user.subject,
                expires_in_days=serializer.validated_data["expires_in_days"],
            )
        except InvalidApprovalState as error:
            raise InvalidApprovalResponse from error
        return Response(
            {
                **ApprovalRequestSerializer(approval_link.request).data,
                "approval_url": approval_link.url,
            },
            status=status.HTTP_201_CREATED,
        )


class ApprovalLinkView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, token):
        try:
            approval_request = get_active_approval_request(token)
        except InvalidApprovalLink:
            raise exceptions.NotFound()
        return Response(
            {
                **ApprovalRequestSerializer(approval_request).data,
                "post": PostSerializer(approval_request.post).data,
            }
        )


class ApprovalLinkDecisionView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, token):
        serializer = ApprovalDecisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            approval_request = decide_approval(raw_token=token, **serializer.validated_data)
        except InvalidApprovalLink:
            raise exceptions.NotFound()
        except (ApprovalAlreadyDecided, InvalidApprovalState) as error:
            raise InvalidApprovalResponse from error
        return Response(ApprovalRequestSerializer(approval_request).data)


class ApprovalRequestDetailView(TenantScopedAPIView):
    required_scope = "approvals:write"
    required_roles = ("OWNER", "MANAGER", "CONTENT_CREATOR")

    def delete(self, request, approval_request_id):
        approval_request = get_object_or_404(
            ApprovalRequest.objects.select_related("post"),
            id=approval_request_id,
            brand__workspace=self.get_tenant(),
            brand_id__in=request.user.brand_ids,
        )
        try:
            revoke_approval(
                approval_request=approval_request,
                tenant=self.get_tenant(),
                subject=request.user.subject,
            )
        except ApprovalAlreadyRevoked as error:
            raise InvalidApprovalResponse from error
        return Response(status=status.HTTP_204_NO_CONTENT)


class PublicationCollectionView(TenantScopedAPIView):
    required_scope = "publications:write"
    required_roles = ("OWNER", "MANAGER", "CONTENT_CREATOR")

    def post(self, request):
        idempotency_key = request.headers.get("Idempotency-Key")
        if not idempotency_key or len(idempotency_key) > 255:
            raise ValidationError(
                {"Idempotency-Key": "This header is required and has a maximum of 255 characters."}
            )

        serializer = PublicationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        tenant = self.get_tenant()
        post_variant = get_object_or_404(
            PostVariant.objects.select_related("post"),
            id=serializer.validated_data["post_variant_id"],
            post__tenant=tenant,
            post__brand_id__in=request.user.brand_ids,
        )
        channel_connection = get_object_or_404(
            ChannelConnection.objects.select_related("social_account"),
            id=serializer.validated_data["channel_connection_id"],
            social_account__tenant=tenant,
            social_account__brand_id=post_variant.post.brand_id,
        )
        try:
            result = schedule_publication(
                tenant=tenant,
                brand=self.get_brand(post_variant.post.brand_id),
                subject=request.user.subject,
                post_variant=post_variant,
                channel_connection=channel_connection,
                scheduled_for=serializer.validated_data["scheduled_for"],
                idempotency_key=idempotency_key,
            )
        except IdempotencyConflict as error:
            raise IdempotencyConflictResponse from error
        except (InvalidSchedule, InvalidStateTransition) as error:
            raise InvalidStateResponse from error

        response_status = status.HTTP_201_CREATED if result.created else status.HTTP_200_OK
        return Response(PublicationSerializer(result.publication).data, status=response_status)


class PublicationDetailView(TenantScopedAPIView):
    required_scope = "publications:read"
    required_roles = ("OWNER", "MANAGER", "CONTENT_CREATOR", "CLIENT_APPROVER", "VIEWER")

    def get(self, request, publication_id):
        publication = get_object_or_404(
            Publication.objects.select_related("post_variant", "channel_connection"),
            id=publication_id,
            tenant=self.get_tenant(),
            brand_id__in=request.user.brand_ids,
        )
        return Response(PublicationSerializer(publication).data)


class MetaOAuthStartView(TenantScopedAPIView):
    required_scope = "connections:write"
    required_roles = ("OWNER", "MANAGER")

    def post(self, request):
        brand_id = request.data.get("brand_id")
        if not brand_id:
            raise ValidationError({"brand_id": "This field is required."})
        try:
            authorization = start_meta_oauth(
                tenant=self.get_tenant(),
                brand=self.get_brand(brand_id),
                subject=request.user.subject,
            )
        except (MetaConfigurationError, TokenEncryptionError) as error:
            raise MetaConfigurationResponse from error
        return Response({"authorization_url": authorization.authorization_url}, status=status.HTTP_201_CREATED)


class MetaOAuthCallbackView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        code = request.query_params.get("code")
        raw_state = request.query_params.get("state")
        if not code or not raw_state:
            raise ValidationError({"detail": "Both code and state are required."})
        try:
            account = complete_meta_oauth(code=code, raw_state=raw_state)
        except InvalidOAuthState as error:
            raise ValidationError({"state": "Invalid, expired or already used OAuth state."}) from error
        except (MetaConfigurationError, TokenEncryptionError) as error:
            raise MetaConfigurationResponse from error
        except MetaProviderError as error:
            raise MetaConnectionResponse from error
        return Response(
            {
                "social_account_id": str(account.id),
                "provider": account.provider,
                "connection_count": account.channel_connections.count(),
            }
        )
