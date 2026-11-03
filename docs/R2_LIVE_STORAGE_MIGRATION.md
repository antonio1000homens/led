# LED live object migration to Cloudflare R2

The publisher and admin status API use the `STATE_STORAGE_BACKEND` setting. The supported values are `s3` and `r2`; `STATE_STORAGE_MIRROR` can be `none`, `s3`, or `r2`. During mirroring, reads come from the primary and each publisher write is copied to the mirror. Mirror failures are logged and do not interrupt publishing.

R2 holds only `state/feed-cache.json` and `api/screens`. The bucket is private. The Worker exposes only `api/screens` at `https://led.alf-broadcast.co.uk/api/screens`. Static assets and the S3 objects remain in the AWS hosting bucket.

## Prerequisites

- Create a private R2 bucket named `led-live-state` (or set `LED_R2_BUCKET_NAME`) with `npx wrangler@4.157.0 r2 bucket create led-live-state`.
- Create bucket-scoped R2 S3 credentials with object read and write access to that bucket.
- Store a JSON SecureString in SSM at `/led/deploy/cloudflare/r2-s3-credentials` with fields `access_key_id` and `secret_access_key`.
- Set the GitHub Actions variables `CLOUDFLARE_ACCOUNT_ID` to the 32-character account ID and `LED_R2_SCREEN_ROUTE_ENABLED=true` when ready to deploy the Worker. Store its separate scoped token in `/led/deploy/cloudflare/r2-worker-api-token`; it needs Workers script and route deployment rights plus R2 binding access. Keep `LED_STATE_STORAGE_BACKEND=s3` until the public route is verified.
- Run `python scripts/migrate-r2-live-data.py seed` with AWS credentials, `boto3` installed, and `STATE_BUCKET`, `CLOUDFLARE_ACCOUNT_ID` set. It seeds both live keys and reads them back to compare SHA-256 hashes.

## Staged migration

1. Deploy with `LED_STATE_STORAGE_BACKEND=s3` and `LED_STATE_STORAGE_MIRROR=r2`. Invoke the publisher once, then run `python scripts/migrate-r2-live-data.py verify` to confirm matching hashes.
2. Set `LED_R2_SCREEN_ROUTE_ENABLED=true` for a deploy so the workflow publishes the Worker. After it succeeds, set it back to `false`; the deployed route remains active. Check the exact public firmware URL from the board's network; require HTTP 200, valid screen JSON, `application/json`, `Cache-Control: no-store, max-age=0`, and a valid `Date` header. Verify `/state/feed-cache.json` is not available through the public route.
3. After the Worker route works from the board network, deploy with `LED_STATE_STORAGE_BACKEND=r2` and `LED_STATE_STORAGE_MIRROR=s3`. Invoke the publisher and verify hashes again. Confirm admin feed status still reports the current feed state.
4. Keep mirroring to S3 for 24 healthy hours. Check publisher refresh, stale-feed recovery, screen fetches, and S3/R2 hash parity. Then deploy with `LED_STATE_STORAGE_MIRROR=none`. Retain the S3 objects for rollback.

The deploy workflow keeps the storage backend at S3 by default. Do not switch the backend before the Worker route returns a valid response from the board's network. If the route fails, set the backend back to S3 and deploy; the S3 copies remain available.

For a workstation smoke check, `curl -fsS -D /tmp/led-screen-headers.txt https://led.alf-broadcast.co.uk/api/screens -o /tmp/led-screens.json`, then check the response headers and validate the JSON with `jq -e '.screens | type == "array"' /tmp/led-screens.json`. This does not replace checking from the board's network.

## Manual object actions

`scripts/migrate-r2-live-data.py` supports `seed` (S3 to R2), `verify` (hash comparison), and `restore` (R2 to S3). It prints hashes and key names only; it never prints object contents or credentials.
