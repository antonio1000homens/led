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
| `steam_train` | Local animation | `enabled`, `animation_speed` (pixels/second), `words` (default `choo choo`) |
| `departures` | National Rail | `enabled`, `poll_seconds`, `screen_duration_seconds` |
| `thorpe_park` | Queue-Times park 2 | `enabled`, `poll_seconds`, `screen_duration_seconds`, ordered `rides` |
| `chessington` | Queue-Times park 3 | `enabled`, `poll_seconds`, `screen_duration_seconds`, ordered `rides` |
| `weather` | Open-Meteo | `enabled`, `poll_seconds`, `overview_enabled`, `screen_duration_seconds`, `today_enabled`, `today_duration_seconds`, `sun_enabled`, `sun_duration_seconds` |
| `calendar` | Todoist | `enabled`, `poll_seconds`, `screen_duration_seconds` |
| `flash` | Pending MQTT event path | `enabled` (starts or stops board MQTT polling), `screen_duration_seconds` (default 5) |
| `recycling` | Home Assistant / local MQTT | `enabled`, `screen_duration_seconds` (20s), `slide_speed` (15px/s), `days_before_collection` (2 local days) |

`poll_seconds` is between 60 and 86400 seconds. Screen duration is between 2 and 300 seconds. Queue-Times `park_id` is implementation metadata and cannot be patched.

The separate Display setting persists the MatrixPortal's apparent brightness at 25%, 50%, 75%, or 100%. The publisher includes it in `/api/screens`, and the board applies it on its next successful screen refresh. The board buttons remain available for temporary local adjustment.

The Steam Train intro is a virtual screen tied to Departures: when both are enabled it is published immediately before the Departures screen, and its duration is calculated from the configured horizontal speed and trailing text width so the complete train/text composition clears the display before Departures begins. Disabling Departures also suppresses the intro.

Weather's three dedicated screens preserve a fixed order: seven-day overview, Today (six four-hour blocks), then sunrise/sunset. Disabling a sub-screen removes only that screen. Leaving Weather enabled while all three sub-screens are disabled keeps the shared Open-Meteo polling/cache and current-weather overlay active.

The standalone **Today · current conditions** screen is a separate virtual `today` feed with its own `enabled` and `screen_duration_seconds` controls (2–300 seconds) on the admin page. It shares the Open-Meteo weather cache but is **not** the Weather section's **Next 24 hours** forecast (`weather-today`). Changing its enabled state or duration never changes the Weather sub-screen settings. If only standalone Today is enabled, shared weather polling remains active.

Deployment settings still own provider credentials, station CRS, weather coordinates, Todoist OAuth storage, AWS resource names, and Cloudflare Access validation metadata. The control API has no endpoint for arbitrary environment variables and its IAM role does not receive National Rail or Todoist credentials.

Recycling is a virtual, **board-only** policy, not a Lambda provider. The admin card persists `recycling` in DynamoDB. The publisher includes its non-secret policy under `mqtt.recycling` in `/api/screens`. During rollout the MatrixPortal also accepts the former root-level `recycling` field. The MatrixPortal combines this policy with an independently retained `bin_collection` message on `led/screens/+`, applies the duration and scroll-speed overrides to a copy and gates by the synchronized Europe/London date (0–14 days before collection, including collection day). It does not mutate the MQTT snapshot or its expiry. Disabled recycling does not disable MQTT reminders. Admin health is intentionally `unavailable` for an enabled recycling feed: the backend cannot observe the board's local broker or collection date. The browser simulator has only a manual fixture preview, not live MQTT status.

**Cross-repository deployment order:** deploy the LED backend and MatrixPortal firmware first, then merge/deploy the Home Assistant publisher change (see [LED #244](https://github.com/antonio1000homens/led/issues/244)). The Home Assistant publisher will no longer hide snapshots outside the two-day window; old board firmware could otherwise display them earlier than intended. The producer retains `duration_seconds`/`slide_speed` for compatibility, but the new LED admin policy takes precedence.

For Flash events, the runtime `enabled` setting is applied on the MatrixPortal as well as by the publisher: disabled means the board disconnects from MQTT and does not poll the transport. The local `MQTT_ENABLED` and `MQTT_ENABLE_EXPERIMENTAL` settings remain hard safety gates; runtime enablement cannot override either local gate.

If the DynamoDB item does not exist, callers see safe defaults derived from the deployment configuration. The first authenticated configuration read seeds those defaults as version 1. After that, the DynamoDB values are authoritative for supported runtime fields. Existing persisted configs are upgraded in memory without a DynamoDB reset. Weather backfill defaults the seven-day overview to enabled/8 seconds, Today to enabled/8 seconds, and sunrise/sunset to enabled/6 seconds. These are screen-level controls only; there are no `day_0_*` through `day_6_*` settings.

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

### Set MatrixPortal brightness

`PATCH /api/control/v1/display` accepts `brightness_percent` at 25, 50, 75, or 100. It uses the same ETag or `config_version` concurrency check and publisher rebuild as feed changes.

## Cloudflare Access setup

Cloudflare Access is configured in the Windsor Zero Trust account rather than managed by this repository. The applications use the existing Google identity provider. Keep the shared `email and github access` policy unchanged: it is used by 11 applications. The `home1000homens` Allow policy is attached to both LED admin applications alongside the shared policy.

Use two path-scoped Access applications so the Home Assistant service token never grants access to the HTML admin page:

1. Protect `https://<led-host>/admin*` with the shared human allow policy and the `home1000homens` Allow policy.
2. Protect `https://<led-host>/api/control/v1/*` with the same human policies. If Home Assistant uses a Cloudflare service token, add its own Service Auth policy to this API application only; never attach Service Auth to the HTML admin application. The live API application had no Service Auth policy when checked on 4 October 2026, so Home Assistant service-token access is unverified.
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

## Flash events

The `flash` setting owns only operational controls for transient events. It
does not make the backend ingest Alexa reminders. The Home Assistant publisher
owns the event payload and publishes it to
the board's configured MQTT topic. Both board-local MQTT gates default to
enabled; the broker remains board-local, and the listener waits 30 seconds
after display/client initialization before connecting. Runtime Flash
enablement remains an independent gate.
The public `/api/screens` response carries the effective non-secret `flash`
settings so the board can apply admin changes on its normal HTTP refresh path;
it never carries broker credentials or reminder payloads.

The MatrixPortal also subscribes at QoS 1 to
`led/flash/assistant-response` for living-room Assist replies. The version 1
payload has `type: "assistant_response"`, `event: "due"`, a unique `id`,
`label`, matching ISO-8601 `due_at` and `published_at`, an `expires_at` exactly
120 seconds later, `source: "homeassistant"`, and `room: "living_room"`.
Replies pause and resume the same screen rotation as reminders, with a fixed
`ASSISTANT` heading and compact quote-style text. Words wrap to rows of up to
42 characters, with up to three rows per page; each page remains visible for 2.5 seconds, and the flash
duration extends when needed to show every page. Replies are deduplicated and
expire independently; they never change the pending reminder snapshot. An active
reminder suppresses replies, a due reminder interrupts a reply, and a newer
reply replaces an older reply. Connected MQTT servicing checks for new events
every 1.5 seconds with the socket read bounded below one display frame. The
producer contract is tracked in [Home Assistant #41](https://github.com/antonio1000homens/homeassistant/issues/41);
the board consumer is tracked in [LED #251](https://github.com/antonio1000homens/led/issues/251).

## Local development and testing

Production authentication has no bypass flag. Unit tests inject a test signing key/JWK client or mock the authenticator at the Lambda boundary. This keeps local tests deterministic without adding a production environment variable that could accidentally disable authentication.

Run the repository suite with:

```bash
python -m pip install -r requirements-server.txt
bash scripts/run-tests.sh
```

For end-to-end testing, use the public LED hostname through Cloudflare Access. Calling the generated API Gateway URL without a valid `Cf-Access-Jwt-Assertion` must return `401`.

## Seed and reset

The DynamoDB table is retained across stack replacement/deletion. The control plane stores a single item with `config_id=runtime`.

To seed a new installation, deploy the stack and perform an authenticated `GET /api/control/v1/config`; the control Lambda conditionally writes version 1 from deployment defaults.

Reset is intentionally not exposed through the control API. An operator with separate AWS administration rights can delete only the `runtime` item from the `led-runtime-config` table, then perform an authenticated configuration GET to reseed it. Take care: this discards the current runtime settings and ride selections.


## Google Calendar football fixtures

The football_fixtures feed is separate from Todoist calendar. The normal authenticated PATCH /api/control/v1/feeds/football_fixtures accepts enabled, poll_seconds (default 900), screen_duration_seconds (default 20), and lookahead_days (1–180, default 45). Control API status exposes health/staleness without calendar IDs, OAuth tokens, or raw events. Configure the SSM SecureString separately as described in [the football source contract](football-mqtt.md#backend-sourced-pre-football-fixtures-275).
