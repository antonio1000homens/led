# AWS deployment

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

## Deployment conventions

This repository follows the same deployment/secret conventions as `antonio1000homens/scouts` while keeping LED resources isolated:

- GitHub Actions obtains AWS credentials through GitHub OIDC; there are no long-lived AWS access-key secrets.
- `BW_ACCESS_TOKEN` is the Bitwarden Secrets Manager machine-account token stored as a GitHub Actions secret.
- GitHub repository variables contain non-secret deployment configuration or Bitwarden secret UIDs only.
- `bitwarden/sm-action` is pinned to a commit SHA and resolves the National Rail and Cloudflare secret values only at deploy time.
- the National Rail token flows through a `NoEcho` CloudFormation parameter into the Lambda environment.
- Todoist uses OAuth. Its client credentials plus current access/refresh tokens live in an SSM Parameter Store **Standard `SecureString`** named `/led/todoist/oauth`; Lambda can decrypt and update only that parameter so rotating refresh tokens persist without a Secrets Manager per-secret charge.
- Cloudflare's API token is deployment-only and never reaches Lambda.
- Cloudflare DNS is explicitly constrained to the **Windsor** Cloudflare account; deployment must not use the Scouts account.
- the bootstrap stack owns a dedicated private LED Lambda artifact bucket and the CloudFormation execution role.

The implementation deliberately improves on the older Scouts S3 website-origin setup by keeping S3 private and using CloudFront Origin Access Control (OAC).

## Required Bitwarden secrets

Create these in the LED Bitwarden project and allow the `led-github-actions` machine account to read them:

1. `NATIONAL_RAIL_TOKEN` — National Rail Darwin token.
2. `CF_DEPLOY_API_TOKEN` — a Cloudflare API token with Zone Read and DNS Edit access to `alf-broadcast.co.uk` in the **Windsor Cloudflare account**.

Todoist OAuth credentials are **not** stored in Bitwarden/GitHub for runtime use. They are seeded directly into SSM Parameter Store by `scripts/bootstrap-todoist-oauth.py` and thereafter updated by the publisher Lambda when Todoist rotates refresh tokens.

Do not put secret values in GitHub variables. If the existing `CF_DEPLOY_API_TOKEN` value was created for the Scouts account, replace it with a Windsor-scoped token before deployment; the GitHub variable continues to contain only its Bitwarden UID.

## GitHub repository settings

### Secret

- `BW_ACCESS_TOKEN` — Bitwarden machine-account access token for the dedicated LED machine account.

### Variables

Required:

- `AWS_ROLE_TO_ASSUME` — output `AwsRoleToAssume` from the bootstrap stack.
- `CLOUDFORMATION_ROLE_ARN` — output `CloudFormationRoleArn` from the bootstrap stack.
- `CLOUDFLARE_ACCOUNT_ID` — the 32-character Cloudflare account ID for the **Windsor** account.
- `BW_NATIONAL_RAIL_TOKEN` — Bitwarden secret UID for the National Rail token.
- `BW_SECRET_ID_CF_DEPLOY_API_TOKEN` — Bitwarden secret UID for the Windsor Cloudflare deployment token.

Optional:

- `LED_DOMAIN_NAME` — defaults to `led.alf-broadcast.co.uk`.
- `LED_CF_ZONE_NAME` — defaults to `alf-broadcast.co.uk`.
- `LED_CALENDAR_SOURCE` — defaults to `off`; set to `todoist` only after OAuth bootstrap succeeds.
- `LED_TODOIST_CACHE_SECONDS` — defaults to `300`.
- `LED_TODOIST_MAX_EVENTS` — defaults to `6`.
- `LED_TODOIST_FILTER_QUERY` — defaults to `date after: yesterday`.
- `LED_TODOIST_TIMEZONE` — defaults to `Europe/London`.
- `LED_CALENDAR_DURATION_SECONDS` — defaults to `10`.
- `LED_CALENDAR_PAGE_SECONDS` — defaults to `5`.

`CODE_BUCKET` is intentionally **not** a GitHub variable. CI derives `led-code-eu-west-2-<aws-account-id>` after assuming the LED AWS role and verifies that the bucket exists. If an old `CODE_BUCKET` repository variable was created during initial setup, it can be removed because the workflow no longer reads it.

Unlike the current Scouts website workflow, LED does not store the CloudFront distribution ID in Bitwarden. It is non-secret stack output metadata and is read directly from CloudFormation during deployment.

The deploy workflow validates the required `BW_*` secret-ID variables as UUID-shaped values before invoking Bitwarden Actions. It also validates `CLOUDFLARE_ACCOUNT_ID` and `LED_CALENDAR_SOURCE`. These checks fail without echoing secret values.

The Cloudflare DNS helper then queries the zone using both the zone name and `account.id`, and verifies that the returned zone belongs to an account named `Windsor` before any create/update request. A Scouts account ID/token therefore fails closed instead of writing to the wrong account.

## First-time AWS bootstrap

The AWS account needs a GitHub Actions OIDC provider. If one already exists, the LED bootstrap script reuses it; otherwise the script creates the account-level provider.

Run with an AWS principal that is allowed to create IAM roles and S3 buckets:

```bash
AWS_PROFILE=<admin-profile> \
bash scripts/bootstrap-deployment-role.sh
```

The `led-bootstrap` stack creates:

- `GitHubActionsLedDeployRole`, trusted only for `antonio1000homens/led` on `master`;
- `LedCloudFormationExecutionRole`, used by CloudFormation for the LED infrastructure;
- `led-code-eu-west-2-<aws-account-id>`, a dedicated encrypted/private Lambda artifact bucket with public access blocked and TLS-only access enforced.

The SSM Todoist parameter is intentionally **not** created by CloudFormation because `AWS::SSM::Parameter` does not support creating `SecureString` parameters. `scripts/bootstrap-todoist-oauth.py` creates or updates `/led/todoist/oauth` directly as a Standard `SecureString`; the main stack only grants the publisher narrowly-scoped `ssm:GetParameter`/`ssm:PutParameter` access to that path.

The code bucket is retained if the bootstrap stack is deleted, preventing accidental loss of deployment artifacts.

Copy the two role output ARNs into `AWS_ROLE_TO_ASSUME` and `CLOUDFORMATION_ROLE_ARN`. `CodeBucketName` is informational; CI derives the same deterministic bucket name automatically.

## Automated deployment

A push to `master`, or a manual `workflow_dispatch`, performs the production deployment:

1. run all Python unit/infrastructure tests;
2. validate Bitwarden UID variables, `LED_CALENDAR_SOURCE`, and the Windsor `CLOUDFLARE_ACCOUNT_ID`;
3. resolve the National Rail and Windsor Cloudflare secrets through the LED Bitwarden machine account;
4. assume the repo-scoped AWS role using GitHub OIDC;
5. derive and verify the dedicated `led-code-eu-west-2-<aws-account-id>` bucket;
6. request or reuse the `led.alf-broadcast.co.uk` ACM certificate in `us-east-1`;
7. create/update the ACM validation CNAME in the Windsor Cloudflare account and wait for issuance;
8. package the Lambda, including `zeep` and the Todoist OAuth/provider module, and upload it to the dedicated LED code bucket;
9. deploy `infrastructure/led-stack.yaml` through `LedCloudFormationExecutionRole`, configuring Lambda access to `/led/todoist/oauth`;
10. upload `simulator/index.html` as S3 `index.html`;
11. invoke the publisher once so `/api/screens` exists immediately;
12. create/update the proxied `led.alf-broadcast.co.uk` CNAME in the Windsor Cloudflare account so Cloudflare Access can enforce the admin and control-API applications;
13. invalidate `/index.html` and `/api/screens`.

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

4. Set GitHub repository variable `LED_CALENDAR_SOURCE=todoist` and run the deployment workflow. Optional Todoist filter/timing settings can be set through the other `LED_TODOIST_*`/`LED_CALENDAR_*` variables above.

No Todoist Client Secret, access token or refresh token is placed in GitHub Actions variables, CloudFormation parameters, `/api/screens`, S3 feed state, simulator code or MatrixPortal configuration.

### Migrating the previous Secrets Manager OAuth secret

If OAuth was already bootstrapped into the old Secrets Manager resource, do **not** authorize Todoist again. Before enabling/deploying the SSM-backed runtime, copy the existing JSON into the Standard `SecureString`:

```bash
AWS_PROFILE='<aws-profile>' \
python3 scripts/bootstrap-todoist-oauth.py \
  --migrate-secret-id '<existing-secrets-manager-arn>'
```

The migration reads the existing secret without printing it, validates that the Todoist client credentials and refresh token are present, then writes the same JSON to `/led/todoist/oauth` with `Type=SecureString`, `Tier=Standard`, and `Overwrite=true`.

After the SSM-backed stack has deployed and the Todoist calendar is verified, schedule the old Secrets Manager secret for deletion:

```bash
AWS_PROFILE='<aws-profile>' aws secretsmanager delete-secret \
  --region eu-west-2 \
  --secret-id '<existing-secrets-manager-arn>' \
  --recovery-window-in-days 7
```

AWS makes a secret inaccessible as soon as it is scheduled for deletion and does not charge for secrets marked for deletion during the recovery window. Keep the recovery window rather than forcing immediate deletion so the migration remains reversible for seven days.

### Runtime refresh-token rotation

New Todoist applications issue short-lived access tokens and rotating refresh tokens. The publisher decrypts the SSM `SecureString`, reuses a still-valid access token, and refreshes shortly before expiry. Every successful refresh is persisted immediately because the returned refresh token replaces the consumed token.

If Todoist returns `401` for an API request, the provider forces one refresh and retries the task request once. The code also treats a refresh response that omits the replacement refresh token as unrecoverable rather than persisting/replaying the consumed token. In that case the calendar becomes stale/unavailable and the OAuth bootstrap script must be run again.

The default filter means scheduled tasks from today onward are eligible. `LED_TODOIST_FILTER_QUERY` can be narrowed to a project/label/other Todoist filter without changing code. The provider independently sorts the returned tasks and retains only the next configured events, so API response order is not relied upon.

## Cloudflare account safety

There are separate Scouts and Windsor Cloudflare accounts. LED is explicitly a Windsor service.

Set `CLOUDFLARE_ACCOUNT_ID` to the **Windsor** account ID. The deployment helper calls Cloudflare's zone-list API with an `account.id` filter and verifies the returned account name is `Windsor` before modifying DNS. The API token must also have access to the `alf-broadcast.co.uk` zone in that account.

The Scouts Cloudflare account ID must never be configured for LED.

## Manual deployment

For diagnosis or a first deploy outside GitHub Actions, resolve the required deployment secret values locally first and provide the Windsor account ID:

```bash
export NATIONAL_RAIL_TOKEN='<resolved value>'
export CF_DEPLOY_API_TOKEN='<resolved Windsor Cloudflare token>'
export CLOUDFLARE_ACCOUNT_ID='<Windsor Cloudflare account id>'
export CLOUDFORMATION_ROLE_ARN='<bootstrap stack output>'

bash scripts/deploy.sh
```

For a Todoist-enabled deployment, OAuth must already have been bootstrapped into SSM Parameter Store; then only set:

```bash
export LED_CALENDAR_SOURCE=todoist
```

`deploy.sh` derives the dedicated code bucket from the active AWS account. `CODE_BUCKET` may still be supplied explicitly for diagnosis, but normal LED deployments should use the bootstrap-created bucket.

The component scripts can also be run independently:

```bash
bash scripts/request-acm-certificate.sh
bash scripts/configure-cloudflare-dns.sh
bash scripts/package-lambda.sh
bash scripts/deploy-stack.sh
bash scripts/deploy-static.sh
python3 scripts/bootstrap-todoist-oauth.py
```

`configure-cloudflare-dns.sh` keeps ACM validation DNS-only but proxies the LED hostname through Cloudflare. CloudFront remains the HTTPS/CDN endpoint and presents the ACM certificate for `led.alf-broadcast.co.uk`; the proxy is required for Cloudflare Access to enforce the protected admin and control-API paths.

## Runtime behaviour

EventBridge Scheduler invokes `led-publisher` once per minute. The Lambda loads the previous state from S3 and independently applies the configured refresh intervals:

- National Rail: 60 seconds;
- Thorpe Park / Queue-Times: 300 seconds;
- Todoist calendar: 300 seconds when enabled;
- Open-Meteo weather: 600 seconds.

If a feed refresh fails after a prior successful result, the last successful data remains in the published screen payload with `stale: true`. Because this cache lives in S3, it works across Lambda cold starts and separate invocations. A cold Todoist/OAuth failure affects only the calendar screen; rail/queue/weather screens continue to publish. A successful Todoist response with no qualifying tasks is not an error and renders `No upcoming events`.

The Lambda replaces `api/screens` with one complete S3 `PutObject`; S3 object replacement is atomic, so readers never observe partially written JSON.

CloudFront caching is disabled for `api/screens`. Static `index.html` uses normal bounded caching and is invalidated after deployment.

## MatrixPortal

Configure the physical board with:

```python
SCREEN_SOURCE = "api"
SCREEN_API_URL = "https://led.alf-broadcast.co.uk"
POLL_SECONDS = 30
```

The client continues to request `${SCREEN_API_URL}/api/screens`; no National Rail, Todoist, Queue-Times, Open-Meteo, AWS, Cloudflare, Bitwarden or OAuth credentials are stored on the MatrixPortal.

## Cost characteristics

There is no always-on EC2, ECS/Fargate, App Runner, API Gateway, NAT Gateway, or Secrets Manager runtime dependency. Todoist OAuth state is stored in one SSM Parameter Store **Standard `SecureString`** using the default AWS-managed SSM key. The dedicated Lambda code bucket stores only deployment packages. Lambda, Scheduler, S3, CloudFront and standard Parameter Store usage should remain very small at this project's scale, subject to the account's aggregate usage and current AWS pricing.
