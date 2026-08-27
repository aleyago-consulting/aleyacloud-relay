# Relay by Alya Cloud

Relay is Alya Cloud's independent, API-first SaaS for agencies and local
businesses: it plans, creates, approves and publishes social content, then
helps demonstrate which publications generate commercial activity. Its public
site is relay.aleyacloud.com.

It is an independent product. Any future external system interacts with Relay
only through the versioned HTTP API and its documented contracts; it must not
import Relay code or share its database.

## Current scope

This repository contains a technical foundation and an early API prototype.
The agreed agency MVP adds brands, members and roles, client approval links,
brand voice, UTM attribution and publication metrics. The existing code is not
yet a releasable implementation of that complete MVP.

The first functional release supports Meta only (Facebook Pages and Instagram
Professional Accounts), text with one image, scheduled publishing, retry
attempts and auditable outcomes. It does not include a CRM, ads, an inbox,
Google Business, LinkedIn or TikTok.

## Web application

The product interface lives in `frontend/`: React, TypeScript, Vite, Tailwind
CSS and Lucide icons. It is served under `/app/` by a dedicated private
frontend container; Django remains the API and background-work backend.

## Local setup

1. Copy .env.example to .env and set non-development secrets.
2. Start PostgreSQL and Redis with docker compose up -d postgres redis.
3. Create a virtual environment and install the project: pip install -e ".[dev]".
4. Run python manage.py migrate and then start the server with
   python manage.py runserver.

The API health check is available at GET /api/v1/health/. The current
client-facing resource contract is recorded in docs/openapi.yaml. A service
credential must include issuer, audience, expiry, subject, tenant_id and
scopes claims; Relay supports HS256 during the initial deployment.

## Documentation

- [Domain model](DOMAIN.md)
- [Architecture and operational decisions](ARCHITECTURE.md)
- [Product and MVP](PRODUCT.md)
- [Execution plan](docs/MVP-EXECUTION-PLAN.md)
- [Integration contracts](docs/INTEGRATION-CONTRACTS.md)
- [Delivery roadmap](ROADMAP.md)
- [Initial OpenAPI contract](docs/openapi.yaml)
- [Deployment guide](DEPLOYMENT.md)

## Guardrails

- Every business record belongs to one tenant. Tenant selection comes from a
  verified service credential, never a caller-provided header.
- Provider access tokens are encrypted at rest and never returned by the API,
  logged or included in audit metadata.
- Background jobs use idempotency keys and create a PublicationAttempt for
  every provider call.
- PostgreSQL and Redis are required outside tests; SQLite is not a supported
  deployment datastore.
