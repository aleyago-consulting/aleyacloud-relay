from celery import shared_task
from django.utils import timezone

from relay.common.models import LifecycleState
from relay.publications.models import Publication
from relay.publications.services import publish_due_publication


@shared_task
def dispatch_due_publications() -> int:
    due_ids = list(
        Publication.objects.filter(state=LifecycleState.SCHEDULED, scheduled_for__lte=timezone.now())
        .order_by("scheduled_for")
        .values_list("id", flat=True)[:100]
    )
    for publication_id in due_ids:
        publish_publication.delay(str(publication_id))
    return len(due_ids)


@shared_task
def publish_publication(publication_id: str) -> str:
    return publish_due_publication(publication_id=publication_id)
