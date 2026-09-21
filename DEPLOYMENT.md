# AWS deployment

Issue #74 adds a dormant MQTT flash-event path for generic reminder screens.
It is intentionally not enabled: `MQTT_ENABLED` and
`MQTT_ENABLE_EXPERIMENTAL` are both false, and no broker settings or
credentials are committed. Do not enable either gate until Home Assistant
issue #3, the normalized event contract, broker reachability and outage
behaviour have been reviewed together.

When that gate is eventually approved, the board will additionally need the
CircuitPython `adafruit_minimqtt` library copied to `CIRCUITPY/lib`. Until then
the library is intentionally not imported by the normal boot path.

The production LED backend is serverless and publishes a static renderer-neutral snapshot instead of running `server.py` continuously.

```text
EventBridge Scheduler (1 minute)
        |
        v
  led-publisher Lambda <----> SSM Parameter Store
   |      |       |             /led/todoist/oauth SecureString
 Darwin  Queue-  Todoist
         Times      |
   |                |
   +------ Open-Meteo
        |
        v
 private S3 hosting/state bucket
 ├── index.html
 ├── api/screens
 └── state/feed-cache.json
        |
        v
 CloudFront + OAC
        |
 Windsor Cloudflare DNS (proxied for Access)
        |
 led.alf-broadcast.co.uk
   /             \
 browser      MatrixPortal
```

Lambda deployment packages are stored separately in a dedicated private bucket named `led-code-eu-west-2-<aws-account-id>`. The LED project does not use the shared Scouts/general Lambda code bucket.

`state/feed-cache.json` is never exposed through CloudFront. The CloudFront origin policy permits only `index.html` and `api/*`, while Lambda has separate read/write access to the private state object.

> **Privacy:** `/api/screens` is publicly retrievable through CloudFront. The Todoist feed is therefore `off` by default. Enabling it publishes the selected Todoist task names and scheduled dates/times into that public JSON object. Use a deliberately narrow filter/project/label if that exposure is acceptable, or protect/personalize the screen endpoint before enabling private task data.

## Deployment and secret conventions

GitHub Actions and runtime secrets are deliberately separated:

- GitHub Actions authenticates to AWS with GitHub OIDC; there are no long-lived AWS access keys in GitHub.
- deployment-time secrets are AWS Systems Manager Parameter Store **Standard `SecureString`** parameters under `/led/deploy/*`;
- `GitHubActionsLedDeployRole` may read only `/led/deploy/*` and cannot read `/led/todoist/oauth`;
- the workflow assumes the AWS role first, then runs `scripts/load-ssm-secrets.sh`, which decrypts, masks and exports the required values through `GITHUB_ENV`;
- the National Rail token continues to flow through the existing `NoEcho` CloudFormation parameter into the publisher Lambda;
- the Cloudflare API token remains deployment-only and never reaches Lambda;
- Todoist OAuth remains runtime-managed in `/led/todoist/oauth`, which the publisher Lambda can decrypt and update as Todoist rotates refresh tokens;
- Cloudflare DNS is constrained to the **Windsor** account; deployment must not use the Scouts account;
- the bootstrap stack owns the repo-scoped GitHub OIDC role, CloudFormation execution role and dedicated private Lambda artifact bucket.

The deployment parameters are:

```text
/led/deploy/national-rail-token     -> NATIONAL_RAIL_TOKEN
/led/deploy/cloudflare/api-token    -> CF_DEPLOY_API_TOKEN
```

Both are Standard `SecureString` parameters using the default AWS-managed SSM key. No customer-managed KMS permission is required by the GitHub role.

Todoist is intentionally outside that hierarchy:

```text
/led/todoist/oauth
```

Do not move, duplicate or expose the Todoist OAuth parameter to CI.

## GitHub repository settings

GitHub stores only non-secret deployment configuration.

Required variables:

- `AWS_ROLE_TO_ASSUME` — output `AwsRoleToAssume` from the `led-bootstrap` stack.
- `CLOUDFORMATION_ROLE_ARN` — output `CloudFormationRoleArn` from the bootstrap stack.
- `CLOUDFLARE_ACCOUNT_ID` — the 32-character Cloudflare account ID for the **Windsor** account.
- `CF_ACCESS_TEAM_DOMAIN` — the existing Cloudflare Access team domain.
- `CF_ACCESS_AUD` — the existing Cloudflare Access application audience tag.
- `LED_DEPLOY_SSM_PREFIX` — normally `/led/deploy`; the workflow defaults to that value.

Optional variables include `LED_DOMAIN_NAME`, `LED_CF_ZONE_NAME`, `LED_CALENDAR_SOURCE`, the `LED_TODOIST_*` timing/filter settings and the other feed configuration documented in the repository.

`CODE_BUCKET` is intentionally not required as a GitHub variable. CI derives `led-code-eu-west-2-<aws-account-id>` after assuming the LED AWS role and verifies that the bucket exists.

The workflow validates non-secret configuration before AWS authentication. Secret existence/readability is then validated by the SSM loader after OIDC succeeds. Missing or unreadable parameters fail the deployment without printing their values.

## First-time AWS bootstrap

The AWS account needs a GitHub Actions OIDC provider. If one already exists, the LED bootstrap script reuses it; otherwise the script creates the account-level provider.

Run with an AWS principal allowed to create/update IAM roles and S3 buckets:

```bash
AWS_PROFILE=<admin-profile> \
bash scripts/bootstrap-deployment-role.sh
```

The `led-bootstrap` stack creates or updates:

- `GitHubActionsLedDeployRole`, trusted only for `antonio1000homens/led` on `master`;
- `LedCloudFormationExecutionRole`, used by CloudFormation for the LED infrastructure;
- `led-code-eu-west-2-<aws-account-id>`, a dedicated encrypted/private Lambda artifact bucket;
- the narrowly scoped `ssm:GetParameter` permission for `parameter/led/deploy/*` on the GitHub deploy role.

The SSM deployment secret values are not CloudFormation resources. `AWS::SSM::Parameter` does not create `SecureString` values, so the migration/bootstrap script writes them directly through the authenticated AWS CLI.

The Todoist SSM parameter is also intentionally not created by CloudFormation. `scripts/bootstrap-todoist-oauth.py` creates or updates `/led/todoist/oauth`, while the main runtime stack grants only the publisher its separate runtime access.

## Migrate deployment secrets from Bitwarden to SSM

The repository includes an idempotent migration helper based on the recordings repository pattern:

```text
scripts/bootstrap-ssm-migration.sh
config/bootstrap-ssm-migration.env.example
```

Prerequisites are authenticated `aws`, `gh` and `bws` CLIs plus `jq`.

Create the ignored local config if desired:

```bash
cp config/bootstrap-ssm-migration.env.example config/bootstrap-ssm-migration.env
```

The script normally discovers the Bitwarden logical keys `NATIONAL_RAIL_TOKEN` and `CF_DEPLOY_API_TOKEN`. If discovery is ambiguous, set the existing Bitwarden secret UUIDs locally with `BW_NATIONAL_RAIL_TOKEN` and `BW_CF_DEPLOY_API_TOKEN`. Those variables are IDs only, never secret values.

Validate everything without changing AWS or GitHub first:

```bash
bash scripts/bootstrap-ssm-migration.sh --dry-run
```

Then perform the migration:

```bash
bash scripts/bootstrap-ssm-migration.sh
```

The real run:

1. validates AWS, GitHub and Bitwarden authentication;
2. validates `infrastructure/bootstrap.yaml`;
3. updates the existing `led-bootstrap` stack so `GitHubActionsLedDeployRole` can read only `/led/deploy/*`;
4. reads each Bitwarden value only when it is about to be written;
5. creates/updates `/led/deploy/national-rail-token` and `/led/deploy/cloudflare/api-token` as Standard `SecureString` parameters with overwrite enabled;
6. validates parameter names/types without decrypting or printing values;
7. writes only non-secret GitHub variables (`AWS_ROLE_TO_ASSUME`, `CLOUDFORMATION_ROLE_ARN`, `LED_DEPLOY_SSM_PREFIX`).

Secret values are passed to AWS through restrictive temporary request files/stdin rather than command-line arguments. Rerunning the script is safe and can refresh or rotate the two SSM values from Bitwarden during the migration window.

### Production validation and Bitwarden cleanup

After the parameters exist, run the production deployment workflow and verify:

- Lambda/package deployment succeeds;
- National Rail data is published;
- ACM validation and LED DNS updates succeed in the Windsor Cloudflare account;
- the Todoist screen remains healthy and `/led/todoist/oauth` is unchanged.

Only after that validation should the obsolete GitHub Bitwarden configuration be removed. The old settings were `BW_ACCESS_TOKEN`, `BW_NATIONAL_RAIL_TOKEN` and `BW_SECRET_ID_CF_DEPLOY_API_TOKEN`. They are no longer referenced by the active workflow.

For example, using an authenticated GitHub CLI:

```bash
gh secret delete BW_ACCESS_TOKEN --repo antonio1000homens/led
gh variable delete BW_NATIONAL_RAIL_TOKEN --repo antonio1000homens/led
gh variable delete BW_SECRET_ID_CF_DEPLOY_API_TOKEN --repo antonio1000homens/led
```

Remove the LED Bitwarden machine-account/project access as well if it is not used by any local-development workflow.

### Rotation after migration

During the migration window, rerun `scripts/bootstrap-ssm-migration.sh` after changing the source values in Bitwarden. The script overwrites the existing SSM parameters safely.

After Bitwarden access has been retired, rotate the values directly in Parameter Store using an authenticated administrative workflow that writes a Standard `SecureString` without placing the value in shell history or process arguments. Keep the names unchanged so GitHub requires no workflow change.

## Automated deployment

A push to `master`, or a manual `workflow_dispatch`, performs the production deployment:

1. run the Python unit/infrastructure tests;
2. validate non-secret configuration;
3. assume `GitHubActionsLedDeployRole` using GitHub OIDC;
4. decrypt, mask and export the National Rail and Windsor Cloudflare deployment secrets from `/led/deploy/*`;
5. derive and verify the dedicated `led-code-eu-west-2-<aws-account-id>` bucket;
6. request or reuse the `led.alf-broadcast.co.uk` ACM certificate in `us-east-1`;
7. create/update the ACM validation CNAME in the Windsor Cloudflare account and wait for issuance;
8. package the Lambda and upload it to the dedicated LED code bucket;
9. deploy `infrastructure/led-stack.yaml` through `LedCloudFormationExecutionRole`;
10. upload simulator/admin static content;
11. invoke the publisher once so `/api/screens` exists immediately;
12. verify the Todoist screen when enabled;
13. create/update the proxied LED hostname in Windsor Cloudflare;
14. invalidate the published CloudFront paths.

Subsequent deployments reuse the existing certificate, bucket and DNS records. Todoist OAuth state remains in SSM independently of stack deployments.

## Todoist production configuration

The CloudFormation defaults keep Todoist disabled:

```text
LED_CALENDAR_SOURCE=off
LED_TODOIST_CACHE_SECONDS=300
LED_TODOIST_MAX_EVENTS=6
LED_TODOIST_FILTER_QUERY=date after: yesterday
LED_TODOIST_TIMEZONE=Europe/London
LED_CALENDAR_DURATION_SECONDS=10
LED_CALENDAR_PAGE_SECONDS=5
```

### Initial OAuth exchange

For a new Todoist integration with a Client ID and Client Secret:

1. Keep `LED_CALENDAR_SOURCE=off` initially.
2. In Todoist App Management, register `http://127.0.0.1:8765/callback` as an OAuth redirect URL, or choose another URI and pass it through `TODOIST_REDIRECT_URI`.
3. Run:

```bash
TODOIST_CLIENT_ID='<client-id>' \
AWS_PROFILE='<aws-profile>' \
python3 scripts/bootstrap-todoist-oauth.py
```

The script prompts securely for the Client Secret, requests the read-only `data:read` scope, opens Todoist authorization in the browser, verifies the returned OAuth `state`, exchanges the code at `https://api.todoist.com/oauth/access_token`, and writes the client credentials plus access/refresh tokens into `/led/todoist/oauth` as an SSM Parameter Store Standard `SecureString`. It never prints the Client Secret or tokens.

If a localhost callback is not suitable, run with `--manual` and paste the complete redirected callback URL. If the registered callback differs from the default, set `TODOIST_REDIRECT_URI` or pass `--redirect-uri`.

4. Set GitHub repository variable `LED_CALENDAR_SOURCE=todoist` and run the deployment workflow.

No Todoist Client Secret, access token or refresh token is placed in GitHub Actions variables, CloudFormation parameters, `/api/screens`, S3 feed state, simulator code or MatrixPortal configuration.

### Migrating the previous Secrets Manager OAuth secret

If OAuth was already bootstrapped into the old Secrets Manager resource, do not authorize Todoist again. Copy the existing JSON into the Standard `SecureString`:

```bash
AWS_PROFILE='<aws-profile>' \
python3 scripts/bootstrap-todoist-oauth.py \
  --migrate-secret-id '<existing-secrets-manager-arn>'
```

After the SSM-backed stack has deployed and the Todoist calendar is verified, schedule the old Secrets Manager secret for deletion with a recovery window rather than forcing immediate deletion.

### Runtime refresh-token rotation

New Todoist applications issue short-lived access tokens and rotating refresh tokens. The publisher decrypts `/led/todoist/oauth`, reuses a still-valid access token, and refreshes shortly before expiry. Every successful refresh is persisted immediately because the returned refresh token replaces the consumed token.

If Todoist returns `401`, the provider forces one refresh and retries once. If a refresh response omits the replacement refresh token, the provider fails closed and the OAuth bootstrap must be run again.

## Cloudflare account safety

There are separate Scouts and Windsor Cloudflare accounts. LED is explicitly a Windsor service.

Set `CLOUDFLARE_ACCOUNT_ID` to the **Windsor** account ID. The deployment helper calls Cloudflare's zone-list API with an `account.id` filter and verifies the returned account name is `Windsor` before modifying DNS. The API token must also have access to the `alf-broadcast.co.uk` zone in that account.

The Scouts Cloudflare account ID must never be configured for LED.

## Manual deployment

For diagnosis or a first deployment outside GitHub Actions, obtain the deployment secrets from SSM using an authenticated AWS identity that is allowed to read `/led/deploy/*`, then export them only in the local process environment:

```bash
export NATIONAL_RAIL_TOKEN="$(aws ssm get-parameter --region eu-west-2 --name /led/deploy/national-rail-token --with-decryption --query Parameter.Value --output text)"
export CF_DEPLOY_API_TOKEN="$(aws ssm get-parameter --region eu-west-2 --name /led/deploy/cloudflare/api-token --with-decryption --query Parameter.Value --output text)"
export CLOUDFLARE_ACCOUNT_ID='<Windsor Cloudflare account id>'
export CLOUDFORMATION_ROLE_ARN='<bootstrap stack output>'

bash scripts/deploy.sh
```

For a Todoist-enabled deployment, OAuth must already be bootstrapped into `/led/todoist/oauth`; set `LED_CALENDAR_SOURCE=todoist` as required.

The component scripts can also be run independently:

```bash
bash scripts/request-acm-certificate.sh
bash scripts/configure-cloudflare-dns.sh
bash scripts/package-lambda.sh
bash scripts/deploy-stack.sh
bash scripts/deploy-static.sh
python3 scripts/bootstrap-todoist-oauth.py
```

## Runtime behaviour

EventBridge Scheduler invokes `led-publisher` once per minute. The Lambda loads the previous state from S3 and independently applies the configured refresh intervals:

- National Rail: 60 seconds;
- queue feeds: 300 seconds;
- Todoist calendar: 300 seconds when enabled;
- Open-Meteo weather: 600 seconds.

If a feed refresh fails after a prior successful result, the last successful data remains in the published screen payload with `stale: true`. A cold Todoist/OAuth failure affects only the calendar screen; rail/queue/weather screens continue to publish.

The Lambda replaces `api/screens` with one complete S3 `PutObject`; S3 object replacement is atomic, so readers never observe partially written JSON. CloudFront caching is disabled for `api/screens`.

## MatrixPortal

Configure the physical board with:

```python
SCREEN_SOURCE = "api"
SCREEN_API_URL = "https://led.alf-broadcast.co.uk"
POLL_SECONDS = 30
```

The client requests `${SCREEN_API_URL}/api/screens`; no National Rail, Todoist, Queue-Times, Open-Meteo, AWS, Cloudflare, SSM or OAuth credentials are stored on the MatrixPortal.

## Cost characteristics

There is no always-on EC2, ECS/Fargate, App Runner, NAT Gateway, or Secrets Manager runtime dependency. Deployment secrets and Todoist OAuth state use SSM Parameter Store Standard `SecureString` parameters with the default AWS-managed SSM key. The dedicated Lambda code bucket stores only deployment packages. Lambda, Scheduler, S3, CloudFront and standard Parameter Store usage should remain very small at this project's scale, subject to the account's aggregate usage and current AWS pricing.
