from rest_framework.permissions import BasePermission

from relay.tenancy.models import Membership


class HasRelayScope(BasePermission):
    required_scope: str | None = None

    def has_permission(self, request, view) -> bool:
        required_scope = getattr(view, "required_scope", self.required_scope)
        if not request.user.is_authenticated:
            return False
        if required_scope is not None and required_scope not in request.user.scopes:
            return False

        required_roles = getattr(view, "required_roles", None)
        if required_roles is None:
            return True
        return Membership.objects.filter(
            workspace_id=request.user.workspace_id,
            subject=request.user.subject,
            role__in=required_roles,
            is_active=True,
        ).exists()
