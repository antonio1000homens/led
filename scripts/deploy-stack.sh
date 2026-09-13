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
TODOIST_TOKEN="${TODOIST_TOKEN:-}"
THORPE_PARK_RIDES="${LED_THORPE_PARK_RIDES:-Hyperia,Stealth,The Swarm,SAW - The Ride,Nemesis Inferno,Colossus,Ghost Train,Rush,Detonator,Tidal Wave}"
CALENDAR_SOURCE="${LED_CALENDAR_SOURCE:-off}"

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
  "TodoistToken=${TODOIST_TOKEN}"
  "DomainName=${DOMAIN_NAME}"
  "CertificateArn=${CERTIFICATE_ARN}"
  "ThorpeParkRides=${THORPE_PARK_RIDES}"
  "CalendarSource=${CALENDAR_SOURCE}"
)
if [[ -n "${CLOUDFORMATION_ROLE_ARN:-}" ]]; then
  args+=(--role-arn "${CLOUDFORMATION_ROLE_ARN}")
fi
aws "${args[@]}"
