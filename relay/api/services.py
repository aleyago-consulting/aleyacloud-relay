import hashlib
import json
from dataclasses import dataclass

from django.db import IntegrityError, transaction

from relay.audit.models import AuditLog
from relay.common.models import LifecycleState
from relay.content.models import Post, PostVariant
from relay.publications.models import Publication
from relay.social.models import ChannelConnection
from relay.tenancy.models import Brand, Tenant


class IdempotencyConflict(Exception):
    """The same client key was supplied for a semantically different request."""


class InvalidStateTransition(Exception):
    """A command is not permitted for the resource's current state."""


class InvalidSchedule(Exception):
    """A publication cannot be scheduled with the submitted parameters."""


@dataclass(frozen=True)
class CreatePostResult:
    post: Post
    created: bool


@dataclass(frozen=True)
class SchedulePublicationResult:
    publication: Publication
    created: bool


def request_fingerprint(payload: dict[str, object]) -> str:
    canonical = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=str,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


@transaction.atomic
def create_post_draft(
    *,
    tenant: Tenant,
    brand: Brand,
    subject: str,
    idempotency_key: str,
    payload: dict[str, object],
) -> CreatePostResult:
    fingerprint = request_fingerprint(payload)
    existing = Post.objects.select_for_update().filter(
        tenant=tenant, idempotency_key=idempotency_key
    ).first()
    if existing:
        if existing.request_fingerprint != fingerprint:
            raise IdempotencyConflict
        return CreatePostResult(post=existing, created=False)

    try:
        post = Post.objects.create(
            tenant=tenant,
            brand=brand,
            title=str(payload.get("title", "")),
            body=str(payload["body"]),
            created_by_subject=subject,
            idempotency_key=idempotency_key,
            request_fingerprint=fingerprint,
        )
        PostVariant.objects.create(post=post, body=post.body)
        AuditLog.objects.create(
            tenant=tenant,
            brand=brand,
            actor_type="service",
            actor_id=subject,
            event_type="post.draft_created",
            subject_type="post",
            subject_id=post.id,
            metadata={"idempotency_key": idempotency_key},
        )
    except IntegrityError:
        existing = Post.objects.select_for_update().get(
            tenant=tenant, idempotency_key=idempotency_key
        )
        if existing.request_fingerprint != fingerprint:
            raise IdempotencyConflict
        return CreatePostResult(post=existing, created=False)

    return CreatePostResult(post=post, created=True)


@transaction.atomic
def approve_post(*, post: Post, tenant: Tenant, brand: Brand, subject: str) -> Post:
    post = Post.objects.select_for_update().get(id=post.id, tenant=tenant, brand=brand)
    if post.state == LifecycleState.APPROVED:
        return post
    if post.state not in {LifecycleState.DRAFT, LifecycleState.PENDING_APPROVAL}:
        raise InvalidStateTransition

    post.state = LifecycleState.APPROVED
    post.save(update_fields=("state", "updated_at"))
    AuditLog.objects.create(
        tenant=tenant,
        brand=brand,
        actor_type="service",
        actor_id=subject,
        event_type="post.approved",
        subject_type="post",
        subject_id=post.id,
        metadata={},
    )
    return post


@transaction.atomic
def schedule_publication(
    *,
    tenant: Tenant,
    brand: Brand,
    subject: str,
    post_variant: PostVariant,
    channel_connection: ChannelConnection,
    scheduled_for,
    idempotency_key: str,
) -> SchedulePublicationResult:
    payload = {
        "post_variant_id": str(post_variant.id),
        "channel_connection_id": str(channel_connection.id),
        "scheduled_for": scheduled_for.isoformat(),
    }
    fingerprint = request_fingerprint(payload)
    existing = Publication.objects.select_for_update().filter(
        tenant=tenant, idempotency_key=idempotency_key
    ).first()
    if existing:
        if existing.request_fingerprint != fingerprint:
            raise IdempotencyConflict
        return SchedulePublicationResult(publication=existing, created=False)

    if post_variant.post.tenant_id != tenant.id or post_variant.post.brand_id != brand.id:
        raise InvalidSchedule
    if (
        channel_connection.social_account.tenant_id != tenant.id
        or channel_connection.social_account.brand_id != brand.id
        or not channel_connection.is_active
    ):
        raise InvalidSchedule
    if post_variant.post.state != LifecycleState.APPROVED:
        raise InvalidStateTransition

    try:
        publication = Publication.objects.create(
            tenant=tenant,
            brand=brand,
            post_variant=post_variant,
            channel_connection=channel_connection,
            scheduled_for=scheduled_for,
            state=LifecycleState.SCHEDULED,
            idempotency_key=idempotency_key,
            request_fingerprint=fingerprint,
        )
        AuditLog.objects.create(
            tenant=tenant,
            brand=brand,
            actor_type="service",
            actor_id=subject,
            event_type="publication.scheduled",
            subject_type="publication",
            subject_id=publication.id,
            metadata={"idempotency_key": idempotency_key},
        )
    except IntegrityError:
        existing = Publication.objects.select_for_update().get(
            tenant=tenant, idempotency_key=idempotency_key
        )
        if existing.request_fingerprint != fingerprint:
            raise IdempotencyConflict
        return SchedulePublicationResult(publication=existing, created=False)

    return SchedulePublicationResult(publication=publication, created=True)
