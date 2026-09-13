# LED runtime control plane

The runtime control plane changes operational LED behaviour without rebuilding or redeploying the Lambda package. It is deliberately separate from deployment configuration and secrets.

## Architecture

The scheduled `led-publisher` Lambda still runs once per minute. On every invocation it reads the current runtime configuration from DynamoDB, refreshes only feeds that are enabled and due, preserves last-successful feed state in the private S3 state prefix, and publishes the renderer-neutral `/api/screens` object through CloudFront.

The `led-control-api` Lambda is reached through the same public LED hostname at `/api/control/v1/*`. It validates the Cloudflare Access application JWT itself before reading or mutating configuration. A successful mutation uses a DynamoDB conditional write and asynchronously invokes the publisher so display changes normally apply immediately rather than waiting for the next scheduled tick.

`/api/screens` and the public simulator remain outside Cloudflare Access. `/admin*` and `/api/control/v1/*` are the protected control plane.

## Runtime versus deployment configuration

DynamoDB contains only non-secret settings that are safe to change at runtime. The stable v1 feeds are:

| Feed | Provider | Mutable settings |
| --- | --- | --- |
| `departures` | National Rail | `enabled`, `poll_seconds`, `screen_duration_seconds` |
| `thorpe_park` | Queue-Times park 2 | `enabled`, `poll_seconds`, `screen_duration_seconds`, ordered `rides` |
| `chessington` | Queue-Times park 3 | `enabled`, `poll_seconds`, `screen_duration_seconds`, ordered `rides` |
| `weather` | Open-Meteo | `enabled`, `poll_seconds` |
| `calendar` | Todoist | `enabled`, `poll_seconds`, `screen_duration_seconds` |

`poll_seconds` is between 60 and 86400 seconds. Screen duration is between 2 and 300 seconds. Queue-Times `park_id` is implementation metadata and cannot be patched.

Deployment settings still own provider credentials, station CRS, weather coordinates, Todoist OAuth storage, AWS resource names, and Cloudflare Access validation metadata. The control API has no endpoint for arbitrary environment variables and its IAM role does not receive National Rail or Todoist credentials.

If the DynamoDB item does not exist, callers see safe defaults derived from the deployment configuration. The first authenticated configuration read seeds those defaults as version 1. After that, the DynamoDB values are authoritative for supported runtime fields.

## Control API

All endpoints return JSON and `Cache-Control: no-store`. Configuration responses include an `ETag` containing the current numeric configuration version.

### Read configuration

`GET /api/control/v1/config`

Returns the effective configuration, `config_version`, `updated_at`, `updated_by`, field limits, provider/display metadata, and live ride choices for Queue-Times feeds.

### Read status

`GET /api/control/v1/status`

Returns enabled state, provider, health, last successful refresh, last attempted refresh, stale state and effective polling interval for every feed, plus the timestamp and config version currently published in `/api/screens`. Provider exception bodies and secrets are never returned.

### Read ride choices

`GET /api/control/v1/feeds/{feed_id}/options`

This is available for `thorpe_park` and `chessington`. Choices come from the most recent cached Queue-Times response when possible, with a live Queue-Times lookup as fallback. If Queue-Times is temporarily unavailable, the currently configured ride names remain usable.

### Patch one feed

`PATCH /api/control/v1/feeds/{feed_id}` accepts any subset of that feed's mutable fields. Unknown feed IDs and fields are rejected. Queue-Times ride names are validated case-insensitively against current known rides and stored using the provider's canonical names while preserving the requested order.

Use either `If-Match` with the current ETag or a numeric `config_version` field in the JSON body. A stale version returns `412 Precondition Failed`.

Example after authenticating through Cloudflare Access:

```bash
curl -X PATCH "https://led.alf-broadcast.co.uk/api/control/v1/feeds/chessington" \
  -H 'Content-Type: application/json' \
  -H 'If-Match: "8"' \
  --data '{
    "enabled": true,
    "poll_seconds": 300,
    "screen_duration_seconds": 10,
    "rides": ["Vampire", "Dragon's Fury", "Mandrill Mayhem"]
  }'
```

After the conditional write succeeds, the control Lambda logs the actor type, feed ID, changed fields, old/new version and request ID, then invokes the publisher asynchronously.

## Cloudflare Access setup

The repository intentionally does not contain Cloudflare service-token credentials or a second interactive authentication system. Configure Access on the existing LED hostname using the existing Google identity provider and existing reusable two-user allow policy.

Use two path-scoped Access applications so the Home Assistant service token never grants access to the HTML admin page:

1. Protect `https://<led-host>/admin*` with the existing interactive Google/two-user allow policy only.
2. Protect `https://<led-host>/api/control/v1/*` with the same human allow policy plus a Service Auth policy that includes the dedicated Home Assistant service token.
3. Do not add an Access application covering `https://<led-host>/api/screens` or the public simulator path.

Set these GitHub repository variables before production deployment:

- `CF_ACCESS_TEAM_DOMAIN`: the full Access team domain, for example `https://example.cloudflareaccess.com`.
- `CF_ACCESS_AUD`: the audience tag of the Access application protecting `/api/control/v1/*`.

The backend fetches and caches Access public keys from `<team-domain>/cdn-cgi/access/certs` and validates RS256 signature, issuer, application audience and expiry on every API request. This validation also runs when the API Gateway hostname is called directly, so bypassing Cloudflare does not bypass origin authentication.

Human Access JWTs are audited as `human:<email>`. Service-token JWTs are audited separately as `machine:<service identity>`.

## Home Assistant

Store the Cloudflare service-token values only in Home Assistant secrets, never in this repository:

```yaml
# secrets.yaml
led_cf_access_client_id: "<service-token-client-id>"
led_cf_access_client_secret: "<service-token-client-secret>"
```

A REST sensor can expose the current control-plane status:

```yaml
rest:
  - resource: https://led.alf-broadcast.co.uk/api/control/v1/status
    headers:
      CF-Access-Client-Id: !secret led_cf_access_client_id
      CF-Access-Client-Secret: !secret led_cf_access_client_secret
    scan_interval: 60
    sensor:
      - name: LED Thorpe Park health
        value_template: "{{ value_json.feeds.thorpe_park.health }}"
        json_attributes_path: "$.feeds.thorpe_park"
        json_attributes:
          - enabled
          - poll_seconds
          - last_successful_refresh
          - stale
```

For mutations, first expose `config_version` from `GET /api/control/v1/config`, then send that version with the desired patch. Passing the version in the body avoids needing a dynamically generated `If-Match` header:

```yaml
rest_command:
  led_set_feed:
    url: "https://led.alf-broadcast.co.uk/api/control/v1/feeds/{{ feed_id }}"
    method: PATCH
    headers:
      Content-Type: application/json
      CF-Access-Client-Id: !secret led_cf_access_client_id
      CF-Access-Client-Secret: !secret led_cf_access_client_secret
    payload: >-
      {"config_version": {{ config_version }}, "enabled": {{ enabled | lower }}}
```

The same API maps naturally to REST-backed switches, input-number controls, scripts/buttons and stale/refresh sensors. No Home Assistant-specific fields are stored in DynamoDB.

## Ride selection behaviour

Thorpe Park and Chessington use the same Queue-Times normalization/provider code. Ride selection is ordered. If a previously configured attraction disappears or is renamed upstream, the publisher ignores that missing ride, logs/flags it in the published park screen as `missing_configured_rides`, and continues rendering any remaining configured rides. Every Queue-Times screen retains Queue-Times attribution.

The admin UI obtains choices from the API rather than hard-coding attractions, so new rides can appear without a frontend deployment once Queue-Times reports them.

## Local development and testing

Production authentication has no bypass flag. Unit tests inject a test signing key/JWK client or mock the authenticator at the Lambda boundary. This keeps local tests deterministic without adding a production environment variable that could accidentally disable authentication.

Run the repository suite with:

```bash
python -m pip install -r requirements-server.txt
python -m unittest discover -s tests -v
```

For end-to-end testing, use the public LED hostname through Cloudflare Access. Calling the generated API Gateway URL without a valid `Cf-Access-Jwt-Assertion` must return `401`.

## Seed and reset

The DynamoDB table is retained across stack replacement/deletion. The control plane stores a single item with `config_id=runtime`.

To seed a new installation, deploy the stack and perform an authenticated `GET /api/control/v1/config`; the control Lambda conditionally writes version 1 from deployment defaults.

Reset is intentionally not exposed through the control API. An operator with separate AWS administration rights can delete only the `runtime` item from the `led-runtime-config` table, then perform an authenticated configuration GET to reseed it. Take care: this discards the current runtime settings and ride selections.
