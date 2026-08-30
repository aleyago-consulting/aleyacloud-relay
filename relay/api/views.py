from uuid import UUID
from django.contrib.auth import authenticate, get_user_model, login, logout
from datetime import timedelta
from django.db.models import Count, Prefetch
from django.db.models.functions import TruncDate
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from rest_framework import status
from rest_framework import exceptions
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from relay.api.authentication import panel_principal
from relay.api.permissions import HasRelayScope
from relay.api.serializers import (
    ApprovalDecisionSerializer,
    ApprovalRequestCreateSerializer,
    ApprovalRequestSerializer,
    ChannelConnectionSerializer,
    MediaAssetSerializer,
    MediaUploadIntentSerializer,
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
from relay.content.models import MediaAsset
from relay.content.services import (
    InvalidMediaAsset,
    MediaUploadUnavailable,
    confirm_media_upload,
    create_media_upload_intent,
)
from relay.publications.models import Publication
from relay.social.models import ChannelConnection
from relay.social.crypto import TokenEncryptionError
from relay.social.meta import MetaConfigurationError, MetaProviderError
from relay.social.services import InvalidOAuthState, complete_meta_oauth, start_meta_oauth
from relay.tenancy.models import Brand, Membership, Tenant


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


class MediaUploadResponse(exceptions.APIException):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_detail = "Media storage could not complete the requested operation."
    default_code = "media_storage_unavailable"


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


def panel_context(request, *, user=None) -> dict:
    # DRF replaces ``request._request.user`` with RelayPrincipal after session
    # authentication. Resolve the original Django user from the session when a
    # protected panel endpoint calls this helper.
    if user is None:
        user_id = request.session.get("_auth_user_id")
        if user_id is None:
            raise exceptions.NotAuthenticated()
        try:
            user = get_user_model().objects.get(pk=user_id)
        except get_user_model().DoesNotExist as error:
            raise exceptions.NotAuthenticated() from error

    principal = panel_principal(user, request.session)
    workspace = Tenant.objects.get(id=principal.workspace_id, is_active=True)
    membership = Membership.objects.get(
        workspace=workspace, subject=principal.subject, is_active=True
    )
    user = request._request.user
    brands = list(Brand.objects.filter(id__in=principal.brand_ids).order_by("name"))
    selected_brand_id = request.session.get("relay_brand_id")
    active_brand = next((brand for brand in brands if str(brand.id) == selected_brand_id), None)
    if active_brand is None and brands:
        active_brand = brands[0]
        request.session["relay_brand_id"] = str(active_brand.id)

    workspaces = Tenant.objects.filter(
        memberships__subject=principal.subject,
        memberships__is_active=True,
        is_active=True,
    ).prefetch_related(
        Prefetch("brands", queryset=Brand.objects.filter(is_active=True).order_by("name"))
    ).distinct().order_by("name")

    return {
        "user": {
            "username": user.get_username(),
            "display_name": user.get_full_name() or user.get_username(),
        },
        "workspace": {"id": str(workspace.id), "name": workspace.name},
        "workspaces": [
            {
                "id": str(item.id),
                "name": item.name,
                "brands": [{"id": str(brand.id), "name": brand.name} for brand in item.brands.all()],
            }
            for item in workspaces
        ],
        "selected_brand_id": str(active_brand.id) if active_brand else None,
        "role": membership.role,
        "scopes": sorted(principal.scopes),
        "brands": [
            {"id": str(brand.id), "name": brand.name, "timezone": brand.timezone}
            for brand in brands
        ],
    }


@method_decorator(ensure_csrf_cookie, name="dispatch")
class PanelCsrfView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        return Response({"detail": "CSRF cookie ready."})


@method_decorator(csrf_protect, name="dispatch")
class PanelLoginView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        username = str(request.data.get("username", "")).strip()
        password = str(request.data.get("password", ""))
        user = authenticate(request=request._request, username=username, password=password)
        if user is None:
            raise exceptions.AuthenticationFailed("Usuario o contraseña incorrectos.")
        if not user.is_active:
            raise exceptions.AuthenticationFailed("Este usuario está desactivado.")
        login(request._request, user)
        try:
            return Response(panel_context(request, user=user))
        except exceptions.AuthenticationFailed:
            logout(request._request)
            raise


@method_decorator(csrf_protect, name="dispatch")
class PanelLogoutView(APIView):
    def post(self, request):
        logout(request._request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class PanelMeView(APIView):
    def get(self, request):
        return Response(panel_context(request))


@method_decorator(csrf_protect, name="dispatch")
class PanelWorkspaceView(APIView):
    """Switch the authenticated browser to one of its own workspaces."""

    def post(self, request):
        workspace_id = request.data.get("workspace_id")
        brand_id = request.data.get("brand_id")
        if not workspace_id:
            raise ValidationError({"workspace_id": "This field is required."})
        membership = Membership.objects.filter(
            workspace_id=workspace_id,
            subject=request.user.subject,
            is_active=True,
            workspace__is_active=True,
        ).first()
        if membership is None:
            raise exceptions.NotFound()
        if brand_id and not Brand.objects.filter(
            id=brand_id, workspace=membership.workspace, is_active=True
        ).exists():
            raise exceptions.NotFound()
        request.session["relay_workspace_id"] = str(membership.workspace_id)
        if brand_id:
            request.session["relay_brand_id"] = str(brand_id)
        else:
            request.session.pop("relay_brand_id", None)
        return Response(panel_context(request))


class PanelSummaryView(TenantScopedAPIView):
    required_scope = "posts:read"
    required_roles = ("OWNER", "MANAGER", "CONTENT_CREATOR", "CLIENT_APPROVER", "VIEWER")

    def get(self, request):
        tenant = self.get_tenant()
        publications = Publication.objects.filter(
            tenant=tenant, brand_id__in=request.user.brand_ids
        )
        today = timezone.localdate()
        start_date = today - timedelta(days=6)
        activity_by_day = {
            row["day"].isoformat(): row["count"]
            for row in publications.filter(created_at__date__gte=start_date)
            .annotate(day=TruncDate("created_at"))
            .values("day")
            .annotate(count=Count("id"))
        }
        recent = publications.select_related(
            "post_variant__post", "channel_connection"
        ).order_by("-updated_at")[:8]
        return Response(
            {
                "published": publications.filter(state="PUBLISHED").count(),
                "scheduled": publications.filter(state="SCHEDULED").count(),
                "failed": publications.filter(state="FAILED").count(),
                "connections": ChannelConnection.objects.filter(
                    social_account__tenant=tenant,
                    social_account__brand_id__in=request.user.brand_ids,
                    is_active=True,
                ).count(),
                "activity": [
                    {
                        "date": (start_date + timedelta(days=offset)).isoformat(),
                        "count": activity_by_day.get((start_date + timedelta(days=offset)).isoformat(), 0),
                    }
                    for offset in range(7)
                ],
                "recent_publications": [
                    {
                        "id": str(publication.id),
                        "title": publication.post_variant.post.title or publication.post_variant.body[:80],
                        "state": publication.state,
                        "scheduled_for": publication.scheduled_for,
                        "channel": publication.channel_connection.channel,
                        "account": publication.channel_connection.display_name,
                    }
                    for publication in recent
                ],
            }
        )


class PostCollectionView(TenantScopedAPIView):
    required_scope = "posts:write"
    required_roles = ("OWNER", "MANAGER", "CONTENT_CREATOR")
    required_scopes_by_method = {"GET": "posts:read"}
    required_roles_by_method = {
        "GET": ("OWNER", "MANAGER", "CONTENT_CREATOR", "CLIENT_APPROVER", "VIEWER")
    }

    def get(self, request):
        queryset = Post.objects.filter(
            tenant=self.get_tenant(), brand_id__in=request.user.brand_ids
        ).prefetch_related("variants__media_assets")
        brand_id = request.query_params.get("brand_id")
        if brand_id:
            queryset = queryset.filter(brand=self.get_brand(brand_id))
        return Response(PostSerializer(queryset.order_by("-updated_at")[:100], many=True).data)

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
        except InvalidMediaAsset as error:
            raise ValidationError(
                {"media_asset_ids": "Use between one and ten ready images from the selected brand."}
            ) from error

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


class MediaUploadIntentView(TenantScopedAPIView):
    required_scope = "media:write"
    required_roles = ("OWNER", "MANAGER", "CONTENT_CREATOR")

    def post(self, request):
        serializer = MediaUploadIntentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        brand = self.get_brand(serializer.validated_data.pop("brand_id"))
        try:
            intent = create_media_upload_intent(
                tenant=self.get_tenant(),
                brand=brand,
                subject=request.user.subject,
                **serializer.validated_data,
            )
        except InvalidMediaAsset as error:
            raise ValidationError("The image must be a JPEG or PNG no larger than 10 MB.") from error
        except MediaUploadUnavailable as error:
            raise MediaUploadResponse from error
        return Response(
            {
                "asset": MediaAssetSerializer(intent.asset).data,
                "upload_url": intent.upload_url,
                "upload_headers": {
                    "Content-Type": intent.asset.content_type,
                    **(
                        {"x-amz-meta-sha256": intent.asset.checksum}
                        if intent.asset.checksum
                        else {}
                    ),
                },
            },
            status=status.HTTP_201_CREATED,
        )


class MediaUploadConfirmView(TenantScopedAPIView):
    required_scope = "media:write"
    required_roles = ("OWNER", "MANAGER", "CONTENT_CREATOR")

    def post(self, request, media_asset_id):
        asset = get_object_or_404(
            MediaAsset,
            id=media_asset_id,
            tenant=self.get_tenant(),
            brand_id__in=request.user.brand_ids,
        )
        try:
            asset = confirm_media_upload(
                asset=asset, tenant=self.get_tenant(), subject=request.user.subject
            )
        except InvalidMediaAsset as error:
            raise ValidationError("The uploaded object does not match the requested image.") from error
        except MediaUploadUnavailable as error:
            raise MediaUploadResponse from error
        return Response(MediaAssetSerializer(asset).data)


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
    required_scopes_by_method = {"GET": "publications:read"}
    required_roles_by_method = {
        "GET": ("OWNER", "MANAGER", "CONTENT_CREATOR", "CLIENT_APPROVER", "VIEWER")
    }

    def get(self, request):
        queryset = Publication.objects.filter(
            tenant=self.get_tenant(), brand_id__in=request.user.brand_ids
        ).select_related("post_variant__post", "channel_connection")
        brand_id = request.query_params.get("brand_id")
        if brand_id:
            queryset = queryset.filter(brand=self.get_brand(brand_id))
        return Response(PublicationSerializer(queryset.order_by("-scheduled_for")[:100], many=True).data)

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


class ChannelConnectionCollectionView(TenantScopedAPIView):
    required_scope = "connections:read"
    required_roles = ("OWNER", "MANAGER", "CONTENT_CREATOR", "CLIENT_APPROVER", "VIEWER")

    def get(self, request):
        queryset = ChannelConnection.objects.select_related("social_account").filter(
            social_account__tenant=self.get_tenant(),
            social_account__brand_id__in=request.user.brand_ids,
        )
        brand_id = request.query_params.get("brand_id")
        if brand_id:
            brand = self.get_brand(brand_id)
            queryset = queryset.filter(social_account__brand=brand)
        return Response(ChannelConnectionSerializer(queryset.order_by("display_name"), many=True).data)


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
        # OAuth is a browser journey. Return the user to the selected brand
        # instead of exposing an implementation JSON response after Meta.
        request.session["relay_workspace_id"] = str(account.tenant_id)
        request.session["relay_brand_id"] = str(account.brand_id)
        return redirect("/app/?meta=connected")
