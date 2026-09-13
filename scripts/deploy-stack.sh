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
CF_ACCESS_TEAM_DOMAIN="${CF_ACCESS_TEAM_DOMAIN:?CF_ACCESS_TEAM_DOMAIN is required}"
CF_ACCESS_AUD="${CF_ACCESS_AUD:?CF_ACCESS_AUD is required}"
THORPE_PARK_RIDES="${LED_THORPE_PARK_RIDES:-Hyperia,Stealth,The Swarm,SAW - The Ride,Nemesis Inferno,Colossus,Ghost Train,Rush,Detonator,Tidal Wave}"
CHESSINGTON_RIDES="${LED_CHESSINGTON_RIDES:-Vampire,Dragon's Fury,Mandrill Mayhem}"
CHESSINGTON_CACHE_SECONDS="${LED_CHESSINGTON_CACHE_SECONDS:-300}"
CALENDAR_SOURCE="${LED_CALENDAR_SOURCE:-off}"
TODOIST_CACHE_SECONDS="${LED_TODOIST_CACHE_SECONDS:-300}"
TODOIST_MAX_EVENTS="${LED_TODOIST_MAX_EVENTS:-6}"
TODOIST_FILTER_QUERY="${LED_TODOIST_FILTER_QUERY:-date after: yesterday}"
TODOIST_TIMEZONE="${LED_TODOIST_TIMEZONE:-Europe/London}"
CALENDAR_DURATION_SECONDS="${LED_CALENDAR_DURATION_SECONDS:-10}"
CALENDAR_PAGE_SECONDS="${LED_CALENDAR_PAGE_SECONDS:-5}"

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
  "DomainName=${DOMAIN_NAME}"
  "CertificateArn=${CERTIFICATE_ARN}"
  "CloudflareAccessTeamDomain=${CF_ACCESS_TEAM_DOMAIN}"
  "CloudflareAccessAudience=${CF_ACCESS_AUD}"
  "ThorpeParkRides=${THORPE_PARK_RIDES}"
  "ChessingtonRides=${CHESSINGTON_RIDES}"
  "ChessingtonCacheSeconds=${CHESSINGTON_CACHE_SECONDS}"
  "CalendarSource=${CALENDAR_SOURCE}"
  "TodoistCacheSeconds=${TODOIST_CACHE_SECONDS}"
  "TodoistMaxEvents=${TODOIST_MAX_EVENTS}"
  "TodoistFilterQuery=${TODOIST_FILTER_QUERY}"
  "TodoistTimezone=${TODOIST_TIMEZONE}"
  "CalendarDurationSeconds=${CALENDAR_DURATION_SECONDS}"
  "CalendarPageSeconds=${CALENDAR_PAGE_SECONDS}"
)
if [[ -n "${CLOUDFORMATION_ROLE_ARN:-}" ]]; then args+=(--role-arn "${CLOUDFORMATION_ROLE_ARN}"); fi

set +e
aws "${args[@]}"
status=$?
set -e
if [[ ${status} -ne 0 ]]; then
  echo "CloudFormation deployment failed; recent stack events:" >&2
  aws cloudformation describe-stack-events \
    --region "${AWS_REGION}" \
    --stack-name "${STACK_NAME}" \
    --query 'StackEvents[0:30].[Timestamp,LogicalResourceId,ResourceType,ResourceStatus,ResourceStatusReason]' \
    --output table >&2 || true
  exit "${status}"
fi
