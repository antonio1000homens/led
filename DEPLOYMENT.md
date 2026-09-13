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
 private S3 bucket
 ├── index.html
 ├── api/screens
 └── state/feed-cache.json
        |
        v
 CloudFront + OAC
        |
 Cloudflare DNS (DNS-only)
        |
 led.alf-broadcast.co.uk
   /             \
 browser      MatrixPortal
```

`state/feed-cache.json` is never exposed through CloudFront. The CloudFront origin policy permits only `index.html` and `api/*`, while Lambda has separate read/write access to the private state object.

## Deployment conventions

This repository follows the same deployment/secret conventions as `antonio1000homens/scouts`:

- GitHub Actions obtains AWS credentials through GitHub OIDC; there are no long-lived AWS access-key secrets.
- `BW_ACCESS_TOKEN` is the Bitwarden Secrets Manager machine-account token stored as a GitHub Actions secret.
- GitHub repository variables contain non-secret deployment configuration or Bitwarden secret UIDs only.
- `bitwarden/sm-action` is pinned to a commit SHA and resolves secret values only at deploy time.
- the National Rail token flows through a `NoEcho` CloudFormation parameter into the Lambda environment.
- Cloudflare's API token is deployment-only and never reaches Lambda.

The implementation deliberately improves on the older Scouts S3 website-origin setup by keeping S3 private and using CloudFront Origin Access Control (OAC).

## Required Bitwarden secrets

Create these in the LED Bitwarden project and allow the LED machine account to read them:

1. National Rail Darwin token.
2. Cloudflare API token with permission to edit DNS records in the `alf-broadcast.co.uk` zone.

Do not put either secret value in GitHub variables.

## GitHub repository settings

### Secret

- `BW_ACCESS_TOKEN` — Bitwarden machine-account access token.

### Variables

- `AWS_ROLE_TO_ASSUME` — output `AwsRoleToAssume` from the bootstrap stack.
- `CLOUDFORMATION_ROLE_ARN` — output `CloudFormationRoleArn` from the bootstrap stack.
- `CODE_BUCKET` — Lambda artifact bucket. Defaults in scripts/workflow to `aws2022-lambda-code-eu-west-2-553490163883`.
- `BW_NATIONAL_RAIL_TOKEN` — Bitwarden secret UID for the National Rail token.
- `BW_SECRET_ID_CF_DEPLOY_API_TOKEN` — Bitwarden secret UID for the Cloudflare deployment token.
- `LED_DOMAIN_NAME` — optional; defaults to `led.alf-broadcast.co.uk`.
- `LED_CF_ZONE_NAME` — optional; defaults to `alf-broadcast.co.uk`.

Unlike the current Scouts website workflow, LED does not store the CloudFront distribution ID in Bitwarden. It is a non-secret stack output and is read directly from CloudFormation during deployment, avoiding an unnecessary manually synchronized value.

The deploy workflow validates the two `BW_*` secret-ID variables as UUID-shaped values before invoking Bitwarden Actions. It fails without echoing an invalid value, preventing a literal URL/token from being exposed in Actions logs.

## First-time AWS bootstrap

The account needs a GitHub Actions OIDC provider. If the Scouts bootstrap already created it, the LED bootstrap script reuses it; otherwise the script creates the account-level provider.

Run with an AWS principal that is allowed to create IAM roles:

```bash
AWS_PROFILE=<admin-profile> \
CODE_BUCKET=aws2022-lambda-code-eu-west-2-553490163883 \
bash scripts/bootstrap-deployment-role.sh
```

The `led-bootstrap` stack creates:

- `GitHubActionsLedDeployRole`, trusted only for `antonio1000homens/led` on `main`;
- `LedCloudFormationExecutionRole`, used by CloudFormation for the LED infrastructure.

Copy the two output ARNs into the GitHub variables described above.

## Automated deployment

A push to `main`, or a manual `workflow_dispatch`, performs the production deployment:

1. run all Python unit/infrastructure tests;
2. validate that GitHub secret-ID variables contain Bitwarden UIDs;
3. resolve the National Rail and Cloudflare secrets through the LED Bitwarden machine account;
4. assume the repo-scoped AWS role using GitHub OIDC;
5. request or reuse the `led.alf-broadcast.co.uk` ACM certificate in `us-east-1`;
6. create/update the ACM validation CNAME in Cloudflare and wait for issuance;
7. package the Lambda, including `zeep`, and upload it to `CODE_BUCKET`;
8. deploy `infrastructure/led-stack.yaml` through `LedCloudFormationExecutionRole`;
9. upload `simulator/index.html` as S3 `index.html`;
10. invoke the publisher once so `/api/screens` exists immediately;
11. create/update the DNS-only `led.alf-broadcast.co.uk` CNAME to the CloudFront distribution;
12. invalidate `/index.html` and `/api/screens`.

Subsequent deployments reuse the existing certificate and DNS records.

## Manual deployment

For diagnosis or a first deploy outside GitHub Actions, resolve the two secret values locally first, then run:

```bash
export CODE_BUCKET=aws2022-lambda-code-eu-west-2-553490163883
export NATIONAL_RAIL_TOKEN='<resolved value>'
export CF_DEPLOY_API_TOKEN='<resolved value>'
export CLOUDFORMATION_ROLE_ARN='<bootstrap stack output>'

bash scripts/deploy.sh
```

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

There is no always-on EC2, ECS/Fargate, App Runner, API Gateway, or NAT Gateway component. At the expected one-minute publisher cadence and low display/browser request volume, Lambda, Scheduler, S3, and CloudFront usage should remain very small and typically within or close to AWS free allowances, subject to the account's aggregate usage and current AWS pricing.
