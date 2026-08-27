# Relay deployment

Relay runs as independent web and worker processes. It must have its own
PostgreSQL database, Redis database number/instance, object-storage namespace
and secrets. Do not point it to data stores shared with TavisaSuite, goClinicals
or ClubTrainers.

## Required environment

Set these values in the deployment secret store, never in Git:

- DJANGO_SECRET_KEY
- DJANGO_DEBUG=false
- DJANGO_ALLOWED_HOSTS=relay.aleyacloud.com
- POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_HOST, POSTGRES_PORT
- REDIS_URL
- RELAY_SERVICE_JWT_SECRET, RELAY_SERVICE_JWT_ISSUER, RELAY_SERVICE_JWT_AUDIENCE
- TOKEN_ENCRYPTION_KEY (a Fernet key; generate it with Python's
  cryptography.fernet.Fernet.generate_key())
- B2_ENDPOINT_URL, B2_REGION, B2_BUCKET, B2_APPLICATION_KEY_ID and
  B2_APPLICATION_KEY for Relay's private Backblaze B2 bucket
- Meta OAuth client settings, when the connection flow is enabled

Use independent high-entropy values for Django, Relay JWT and token encryption.
The values in .env.example are local placeholders only.

## Media storage: Backblaze B2

Create one private B2 bucket exclusively for Relay (recommended:
`aleyacloud-relay-media`) and a non-master application key restricted to that
bucket. Scope the key to the `relay/` prefix and give it only the operations
needed by Relay: list, read, write and delete files. Store the key only in the
deployment secret store. Relay uses B2's S3-compatible endpoint and generates a
short-lived signed download URL when Meta must fetch an image; the bucket stays
private and the browser never receives the server application key.

Use the B2 endpoint in the form `https://s3.<region>.backblazeb2.com` and set
the same region in B2_REGION. Set RELAY_MEDIA_URL_TTL_SECONDS to a value long
enough for Meta to fetch the asset (900 seconds initially). Do not set
RELAY_MEDIA_PUBLIC_BASE_URL in production; it remains only as a local-test
compatibility fallback.

Meta must be configured with the exact callback URL
https://relay.aleyacloud.com/api/v1/oauth/meta/callback/. Set the currently
supported Graph API version explicitly in META_GRAPH_VERSION; do not silently
roll a production integration to a new version.

## Initial delivery

1. Clone this repository into `/srv/apps/relay` (not the static landing path).
2. Build and start the private stack:
   `sudo docker compose -f docker-compose.production.yml up -d --build`.
   PostgreSQL and Redis have no host ports; only the web process listens on
   `127.0.0.1:8010`.
3. Run migrations once from the web image:
   `sudo docker compose -f docker-compose.production.yml exec web python manage.py migrate`.
4. Confirm `web`, `worker` and `beat` are running. Beat dispatches due
   publications each minute; the worker has concurrency 1 for the current VPS.
5. Put Nginx in front of the web process and enable TLS for
   relay.aleyacloud.com. A plain upstream example is in deploy/nginx/relay.conf.
   It proxies only to `127.0.0.1:8010`, which is not Internet-exposed.
6. Check GET /api/v1/health/ through the public hostname.

The public root remains the existing static site in /srv/apps/aleya-relay/public.
The application is routed only below /app/ and /api/; do not copy backend
artifacts, credentials or generated app assets to the static public directory.
Merge the locations from deploy/nginx/relay.conf into the existing TLS virtual
host; do not replace the Certbot-managed HTTPS configuration with the port-80
example.

Celery Beat is enabled only after the worker and Meta delivery adapter are in
place. Do not schedule a real publication until Meta credentials and B2 media
delivery have been verified in a non-production workspace.

## Deployment checks

- The database and Redis ports are not exposed publicly.
- Nginx forwards HTTPS traffic only and preserves forwarded-proto headers.
- Logs do not contain authorization headers, OAuth codes or provider tokens.
- Back up PostgreSQL; Redis is only a broker/result backend.
- Restrict object storage to Relay service credentials and short-lived browser
  upload URLs.
