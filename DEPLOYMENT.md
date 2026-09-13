# AWS deployment

The production LED backend is serverless and publishes a static renderer-neutral snapshot instead of running `server.py` continuously.

```text
EventBridge Scheduler (1 minute)
        |
        v
  led-publisher Lambda
   |      |       |
 Darwin  Queue-  Open-
         Times   Meteo
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
 Windsor Cloudflare DNS (DNS-only)
        |
 led.alf-broadcast.co.uk
   /             \
 browser      MatrixPortal
```

Lambda deployment packages are stored separately in a dedicated private bucket named `led-code-eu-west-2-<aws-account-id>`. The LED project does not use the shared Scouts/general Lambda code bucket.

`state/feed-cache.json` is never exposed through CloudFront. The CloudFront origin policy permits only `index.html` and `api/*`, while Lambda has separate read/write access to the private state object.

## Deployment conventions

This repository follows the same deployment/secret conventions as `antonio1000homens/scouts` while keeping LED resources isolated:

- GitHub Actions obtains AWS credentials through GitHub OIDC; there are no long-lived AWS access-key secrets.
- `BW_ACCESS_TOKEN` is the Bitwarden Secrets Manager machine-account token stored as a GitHub Actions secret.
- GitHub repository variables contain non-secret deployment configuration or Bitwarden secret UIDs only.
- `bitwarden/sm-action` is pinned to a commit SHA and resolves secret values only at deploy time.
- the National Rail token flows through a `NoEcho` CloudFormation parameter into the Lambda environment.
- Cloudflare's API token is deployment-only and never reaches Lambda.
- Cloudflare DNS is explicitly constrained to the **Windsor** Cloudflare account; deployment must not use the Scouts account.
- the bootstrap stack owns a dedicated private LED Lambda artifact bucket.

The implementation deliberately improves on the older Scouts S3 website-origin setup by keeping S3 private and using CloudFront Origin Access Control (OAC).

## Required Bitwarden secrets

Create these in the LED Bitwarden project and allow the `led-github-actions` machine account to read them:

1. `NATIONAL_RAIL_TOKEN` — National Rail Darwin token.
2. `CF_DEPLOY_API_TOKEN` — a Cloudflare API token with Zone Read and DNS Edit access to `alf-broadcast.co.uk` in the **Windsor Cloudflare account**.

Do not put either secret value in GitHub variables. If the existing `CF_DEPLOY_API_TOKEN` value was created for the Scouts account, replace it with a Windsor-scoped token before deployment; the GitHub variable continues to contain only its Bitwarden UID.

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

`CODE_BUCKET` is intentionally **not** a GitHub variable. CI derives `led-code-eu-west-2-<aws-account-id>` after assuming the LED AWS role and verifies that the bucket exists. If an old `CODE_BUCKET` repository variable was created while setting up this PR, it can be removed because the workflow no longer reads it.

Unlike the current Scouts website workflow, LED does not store the CloudFront distribution ID in Bitwarden. It is non-secret stack output metadata and is read directly from CloudFormation during deployment.

The deploy workflow validates the two `BW_*` secret-ID variables as UUID-shaped values before invoking Bitwarden Actions. It also validates `CLOUDFLARE_ACCOUNT_ID` as a Cloudflare-style 32-character account ID. These checks fail without echoing secret values.

The Cloudflare DNS helper then queries the zone using both the zone name and `account.id`, and verifies that the returned zone belongs to an account named `Windsor` before any create/update request. A Scouts account ID/token therefore fails closed instead of writing to the wrong account.

## First-time AWS bootstrap

The AWS account needs a GitHub Actions OIDC provider. If one already exists, the LED bootstrap script reuses it; otherwise the script creates the account-level provider.

Run with an AWS principal that is allowed to create IAM roles and S3 buckets:

```bash
AWS_PROFILE=<admin-profile> \
bash scripts/bootstrap-deployment-role.sh
```

The `led-bootstrap` stack creates:

- `GitHubActionsLedDeployRole`, trusted only for `antonio1000homens/led` on `main`;
- `LedCloudFormationExecutionRole`, used by CloudFormation for the LED infrastructure;
- `led-code-eu-west-2-<aws-account-id>`, a dedicated encrypted/private Lambda artifact bucket with public access blocked and TLS-only access enforced.

The code bucket is retained if the bootstrap stack is deleted, preventing accidental loss of deployment artifacts.

Copy the two role output ARNs into `AWS_ROLE_TO_ASSUME` and `CLOUDFORMATION_ROLE_ARN`. `CodeBucketName` is informational; CI derives the same deterministic bucket name automatically.

## Automated deployment

A push to `main`, or a manual `workflow_dispatch`, performs the production deployment:

1. run all Python unit/infrastructure tests;
2. validate Bitwarden UID variables and the Windsor `CLOUDFLARE_ACCOUNT_ID`;
3. resolve the National Rail and Windsor Cloudflare secrets through the LED Bitwarden machine account;
4. assume the repo-scoped AWS role using GitHub OIDC;
5. derive and verify the dedicated `led-code-eu-west-2-<aws-account-id>` bucket;
6. request or reuse the `led.alf-broadcast.co.uk` ACM certificate in `us-east-1`;
7. create/update the ACM validation CNAME in the Windsor Cloudflare account and wait for issuance;
8. package the Lambda, including `zeep`, and upload it to the dedicated LED code bucket;
9. deploy `infrastructure/led-stack.yaml` through `LedCloudFormationExecutionRole`;
10. upload `simulator/index.html` as S3 `index.html`;
11. invoke the publisher once so `/api/screens` exists immediately;
12. create/update the DNS-only `led.alf-broadcast.co.uk` CNAME in the Windsor Cloudflare account;
13. invalidate `/index.html` and `/api/screens`.

Subsequent deployments reuse the existing certificate, bucket, and DNS records.

## Cloudflare account safety

There are separate Scouts and Windsor Cloudflare accounts. LED is explicitly a Windsor service.

Set `CLOUDFLARE_ACCOUNT_ID` to the **Windsor** account ID. The deployment helper calls Cloudflare's zone-list API with an `account.id` filter and verifies the returned account name is `Windsor` before modifying DNS. The API token must also have access to the `alf-broadcast.co.uk` zone in that account.

The Scouts Cloudflare account ID must never be configured for LED.

## Manual deployment

For diagnosis or a first deploy outside GitHub Actions, resolve the two secret values locally first and provide the Windsor account ID:

```bash
export NATIONAL_RAIL_TOKEN='<resolved value>'
export CF_DEPLOY_API_TOKEN='<resolved Windsor Cloudflare token>'
export CLOUDFLARE_ACCOUNT_ID='<Windsor Cloudflare account id>'
export CLOUDFORMATION_ROLE_ARN='<bootstrap stack output>'

bash scripts/deploy.sh
```

`deploy.sh` derives the dedicated code bucket from the active AWS account. `CODE_BUCKET` may still be supplied explicitly for diagnosis, but normal LED deployments should use the bootstrap-created bucket.

The component scripts can also be run independently:

```bash
bash scripts/request-acm-certificate.sh
bash scripts/configure-cloudflare-dns.sh
bash scripts/package-lambda.sh
bash scripts/deploy-stack.sh
bash scripts/deploy-static.sh
```

`configure-cloudflare-dns.sh` uses DNS-only records intentionally. Cloudflare remains the authoritative DNS provider, while CloudFront remains the HTTPS/CDN endpoint and presents the ACM certificate for `led.alf-broadcast.co.uk`.

## Runtime behaviour

EventBridge Scheduler invokes `led-publisher` once per minute. The Lambda loads the previous state from S3 and independently applies the existing refresh intervals:

- National Rail: 60 seconds;
- Thorpe Park / Queue-Times: 300 seconds;
- Open-Meteo weather: 600 seconds.

If a feed refresh fails after a prior successful result, the last successful data remains in the published screen payload with `stale: true`. Because this cache lives in S3, it works across Lambda cold starts and separate invocations.

The Lambda replaces `api/screens` with one complete S3 `PutObject`; S3 object replacement is atomic, so readers never observe partially written JSON.

CloudFront caching is disabled for `api/screens`. Static `index.html` uses normal bounded caching and is invalidated after deployment.

## MatrixPortal

Configure the physical board with:

```python
SCREEN_SOURCE = "api"
SCREEN_API_URL = "https://led.alf-broadcast.co.uk"
POLL_SECONDS = 30
```

The client continues to request `${SCREEN_API_URL}/api/screens`; no National Rail, Queue-Times, Open-Meteo, AWS, Cloudflare, or Bitwarden credentials are stored on the MatrixPortal.

## Cost characteristics

There is no always-on EC2, ECS/Fargate, App Runner, API Gateway, or NAT Gateway component. The dedicated Lambda code bucket stores only deployment packages, so its storage/request cost should be negligible at this project's scale. Lambda, Scheduler, S3, and CloudFront usage should remain very small and typically within or close to AWS free allowances, subject to the account's aggregate usage and current AWS pricing.
