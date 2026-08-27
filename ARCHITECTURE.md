# Relay architecture

## Decision summary

Relay is a standalone Django modular monolith with Django REST Framework,
PostgreSQL, Celery and Redis. It exposes a versioned REST API and owns its own
database, background jobs, object storage namespace and secrets. Nginx sits at
the edge in deployment. This is the smallest architecture that preserves a
clean product boundary while supporting reliable scheduled publication.

Relay is a multi-brand agency workflow, not a single-content scheduler. Its
foundation has Workspace, Brand and Membership authorization; approval links,
brand voice, UTM attribution and publication metrics are first-class domains.
The current implementation establishes the workflow and security boundary; the
panel, media delivery, IA assistance and live Meta delivery remain phased work.

No repository, package, database table or synchronous internal call is shared
with TavisaSuite, goClinicals or ClubTrainers. Those products are API clients.

## Components

    Client products / UI
            │ HTTPS + versioned API
            ▼
     Nginx ─► Django + DRF ─► PostgreSQL (Relay-owned data)
                    │
                    ├──► Redis (broker / scheduling)
                    ▼
                 Celery workers ─► Meta Graph API
                    │
                    └──► object storage (media assets)

The initial code is partitioned by domain: tenancy, social, content,
publications and audit. Cross-domain operations belong in application services
and tasks, not serializers, model signals or client applications.

The partition includes identity/workspaces, brands, approvals and future
attribution/metrics. No CRM, ad management, generic automation engine or
shared AleyaCloud authentication database is introduced.

The architecture reserves a future conversion boundary without enabling it in
the social MVP: LeadCapture, Opportunity, Conversation, Appointment,
ConsentRecord and FollowUpEvent. It receives immutable source/UTM/publication
events through a versioned API, shares the Workspace/Brand authorization model,
and keeps personal data and consent isolated from content analytics. This
prevents a rewrite when conversion is validated, without turning Phase 1 into a
CRM or automation platform.

## API and authentication

The public landing is served from /; the authenticated application lives below
/app/, and its API lives below /api/v1/. Resource shapes and status codes are
in docs/openapi.yaml; changes must be backward compatible within a major
version. Client products authenticate with a Relay-issued, short-lived service
credential. The credential carries immutable workspace and authorized-brand IDs
plus permitted scopes. DRF resolves that context and applies workspace/brand
querysets everywhere. The implemented scopes include posts:write, posts:read,
posts:approve, approvals:write, publications:write and publications:read.

Panel users will authenticate with MFA and receive authorization from a
workspace membership and brand role. Service clients carry only their approved
workspace/brand context and scopes.

The implemented API also requires an active Membership for role-protected
commands. Scopes grant a capability class; roles decide whether the authenticated
subject may exercise it. Owner and manager administer connections, creators can
prepare/approve/schedule content, and viewers are read-only. Client approvals
use a separate unguessable link whose SHA-256 digest alone is persisted; it
expires, supports one decision and only permits reviewing one post.

OAuth is a user-initiated connection flow, separate from client API
credentials. The callback validates state, binds the result to its
pre-authorized tenant and stores encrypted credentials. Encryption keys come
from deployment secrets or a managed KMS; key IDs, not plaintext, may be
recorded for rotation. The implemented Meta flow creates a random state with a
ten-minute expiry, stores only its SHA-256 digest and consumes it once before
the authorization code is exchanged. It discovers Facebook Pages and linked
Instagram Business Accounts without exposing provider access tokens in the API.

## Scheduling and delivery

Creating a publication records scheduled_for in UTC, an idempotency key and an
audit event in the same database transaction. The implemented API only permits
scheduling an approved post variant against an active connection from its own
tenant. Celery finds due rows and a worker atomically claims one before changing
it to PUBLISHING. Every Meta request creates a PublicationAttempt. Transient
failures retry with bounded exponential backoff; permanent errors end as FAILED.
Provider responses are normalized and secrets are never persisted. The delivery
path accepts exactly one image and supports Facebook Page photos and Instagram
Professional image publication through a Relay-controlled media URL.

The final implementation should use row locking/conditional updates to prevent
double publication. Celery is a delivery mechanism, not the source of truth:
PostgreSQL owns the publication state.

Draft creation uses the same tenant-scoped idempotency mechanism now: repeating
the same Idempotency-Key and request returns the original draft; reusing it for
different input returns HTTP 409. Relay records the initial creation as an
AuditLog event in the same transaction.

## Deployment baseline

- Nginx terminates TLS and forwards only application traffic.
- Django web processes and Celery workers use the same immutable application
  image, with distinct commands.
- PostgreSQL and Redis are private network services. Redis is not authoritative
  storage.
- Media resides in a private Backblaze B2 bucket. Browser uploads use narrowly
  scoped signed URLs; workers retrieve media with service credentials and issue
  brief signed download URLs only when Meta must fetch an image.
- Required configuration is supplied through environment variables or a secret
  manager; .env is development-only.

## Deliberate non-decisions

We do not introduce microservices, a provider plugin system, event streaming,
a shared AleyaCloud authentication database or a generic workflow engine at
this stage. Each would add operational cost without serving the Meta MVP.
