# Relay domain model

## Target agency model

The agency MVP supersedes the transitional single-tenant model below. A
Workspace is the isolation root; a Brand is one customer/business within the
workspace. Membership carries the agency or client role. Content, media,
connections, approvals, publications, metrics and attribution all belong to
one Brand and cannot cross its Workspace boundary.

New MVP entities are Brand, Membership, BrandVoice, ApprovalRequest,
ApprovalComment, UTMTemplate, AttributionEvent and PublicationMetric. Client
approval uses a revocable, expiring, digest-only link that grants access solely
to one request. Attribution stores aggregate commercial events by default, not
contacts or form payloads. The detailed target model is in PRODUCT.md.

The future conversion boundary is designed now but not implemented in the
social MVP. It adds LeadCapture, Opportunity, Conversation, Appointment,
ConsentRecord and FollowUpEvent. Every future record remains bound to a Brand,
has an immutable source/campaign/publication relationship where available, and
records the consent basis before any permitted email or WhatsApp follow-up.
Sensitive generated replies require a human approval state. This is a minimal
conversion workflow, not a general CRM.

## Transitional tenant boundary

Tenant (also called a workspace in the API) is Relay's mandatory security and
data-isolation boundary. A tenant is owned by the calling product's customer,
not by the product itself. All mutations and queries are constrained to the
tenant in the verified access token. No API accepts a tenant identifier as an
authority override.

## Core entities

The table below describes the implemented foundation; it will be migrated to
the target Workspace/Brand model in Phase 1 rather than extended ad hoc.

| Entity | Responsibility | Tenant boundary |
| --- | --- | --- |
| Tenant / Workspace | Isolated customer workspace and lifecycle. | Root |
| SocialAccount | Meta identity that completed OAuth. | Direct |
| ChannelConnection | Publishable Facebook Page or Instagram Business Account and its encrypted credentials. | Via social account |
| Post | Canonical content item and editorial state. | Direct |
| PostVariant | Channel-specific text/media rendition of a post. | Via post |
| MediaAsset | Tenant-owned, validated asset referenced by a variant. | Direct |
| Publication | Planned or active release to one channel connection. | Direct |
| PublicationAttempt | Immutable record of a provider call and result. | Via publication |
| AuditLog | Append-only record of material actions. | Direct |

Schedule is represented by Publication.scheduled_for; keeping one entity avoids
two sources of truth for a scheduled delivery.

## Lifecycle

The shared lifecycle vocabulary is:

DRAFT → PENDING_APPROVAL → APPROVED → SCHEDULED → PUBLISHING → PUBLISHED

Terminal alternatives are FAILED and CANCELLED. A retry returns a failed
publication to SCHEDULED only when its retry policy permits it. The allowed
transitions are enforced by the application service, rather than inferred from
the UI. Post uses the editorial portion of the lifecycle; Publication uses the
scheduling and delivery portion.

## Invariants

- A post, its variants, media and publication connection must have the same
  tenant.
- One publication delivers one variant to one channel connection. Publishing
  the same variant to two accounts creates two publications.
- A PostVariant initially supports text plus at most one image. Validation
  rejects other media combinations in the Meta MVP.
- A publication has a tenant-scoped immutable idempotency key supplied by the
  client. Repeating a creation request returns the original publication.
- Every newly created post receives one default variant with the same body.
  This gives API clients a stable identifier to schedule before channel-specific
  variants are introduced.
- PublicationAttempt and AuditLog are append-only. Redaction, if needed,
  removes sensitive values without changing the event identity.

## Provider model: Meta MVP

The only provider in scope is META. Supported channel connection types are
META_FACEBOOK_PAGE and META_INSTAGRAM_BUSINESS_ACCOUNT. OAuth stores the
minimum needed provider identifiers, granted scopes, expiry and encrypted token
material. A token is decrypted only inside the worker immediately before a
provider call; it is never exposed through serializers, logs or audit events.

The model has intentionally no generic provider plugin framework yet. A small,
explicit Meta adapter is enough for the MVP; new providers are a future phase.
