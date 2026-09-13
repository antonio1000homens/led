#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
AWS_REGION="${AWS_REGION:-eu-west-2}"
STACK_NAME="${STACK_NAME:-led-serverless}"
DOMAIN_NAME="${DOMAIN_NAME:-led.alf-broadcast.co.uk}"
CODE_BUCKET="${CODE_BUCKET:?CODE_BUCKET is required}"
CODE_KEY="${CODE_KEY:?CODE_KEY is required}"
CERTIFICATE_ARN="${CERTIFICATE_ARN:?CERTIFICATE_ARN is required}"
NATIONAL_RAIL_TOKEN="${NATIONAL_RAIL_TOKEN:?NATIONAL_RAIL_TOKEN is required}"
THORPE_PARK_RIDES="${LED_THORPE_PARK_RIDES:-Hyperia,Stealth,The Swarm,SAW - The Ride,Nemesis Inferno,Colossus,Ghost Train,Rush,Detonator,Tidal Wave}"
CALENDAR_SOURCE="${LED_CALENDAR_SOURCE:-off}"
TODOIST_CACHE_SECONDS="${LED_TODOIST_CACHE_SECONDS:-300}"
TODOIST_MAX_EVENTS="${LED_TODOIST_MAX_EVENTS:-6}"
TODOIST_FILTER_QUERY="${LED_TODOIST_FILTER_QUERY:-date after: yesterday}"
TODOIST_TIMEZONE="${LED_TODOIST_TIMEZONE:-Europe/London}"
CALENDAR_DURATION_SECONDS="${LED_CALENDAR_DURATION_SECONDS:-10}"
CALENDAR_PAGE_SECONDS="${LED_CALENDAR_PAGE_SECONDS:-5}"
ADMIN_TOKEN_PARAMETER="${LED_ADMIN_TOKEN_PARAMETER:-/led/admin/token}"

# Keep the browser admin bearer token stable across deployments without placing it
# in GitHub. A caller may override ADMIN_TOKEN explicitly for local/bootstrap use.
if [[ -z "${ADMIN_TOKEN:-}" ]]; then
  set +e
  ADMIN_TOKEN="$(aws ssm get-parameter --region "${AWS_REGION}" --name "${ADMIN_TOKEN_PARAMETER}" --with-decryption --query Parameter.Value --output text 2>/dev/null)"
  status=$?
  set -e
  if [[ ${status} -ne 0 || -z "${ADMIN_TOKEN}" || "${ADMIN_TOKEN}" == "None" ]]; then
    ADMIN_TOKEN="$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')"
    aws ssm put-parameter --region "${AWS_REGION}" --name "${ADMIN_TOKEN_PARAMETER}" --type SecureString --value "${ADMIN_TOKEN}" --overwrite >/dev/null
    echo "Created stable LED admin token in SSM parameter ${ADMIN_TOKEN_PARAMETER}" >&2
  fi
fi

args=(
  cloudformation deploy
  --region "${AWS_REGION}"
  --stack-name "${STACK_NAME}"
  --template-file "${ROOT_DIR}/infrastructure/led-stack.yaml"
  --capabilities CAPABILITY_NAMED_IAM
  --parameter-overrides
  "CodeBucket=${CODE_BUCKET}"
  "CodeKey=${CODE_KEY}"
  "NationalRailToken=${NATIONAL_RAIL_TOKEN}"
  "AdminToken=${ADMIN_TOKEN}"
  "DomainName=${DOMAIN_NAME}"
  "CertificateArn=${CERTIFICATE_ARN}"
  "ThorpeParkRides=${THORPE_PARK_RIDES}"
  "CalendarSource=${CALENDAR_SOURCE}"
  "TodoistCacheSeconds=${TODOIST_CACHE_SECONDS}"
  "TodoistMaxEvents=${TODOIST_MAX_EVENTS}"
  "TodoistFilterQuery=${TODOIST_FILTER_QUERY}"
  "TodoistTimezone=${TODOIST_TIMEZONE}"
  "CalendarDurationSeconds=${CALENDAR_DURATION_SECONDS}"
  "CalendarPageSeconds=${CALENDAR_PAGE_SECONDS}"
)
if [[ -n "${CLOUDFORMATION_ROLE_ARN:-}" ]]; then args+=(--role-arn "${CLOUDFORMATION_ROLE_ARN}"); fi
aws "${args[@]}"
