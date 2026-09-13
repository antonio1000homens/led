#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOMAIN_NAME="${DOMAIN_NAME:-led.alf-broadcast.co.uk}"
ZONE_NAME="${ZONE_NAME:-alf-broadcast.co.uk}"
AWS_REGION="${AWS_REGION:-eu-west-2}"
STACK_NAME="${STACK_NAME:-led-serverless}"
CODE_BUCKET="${CODE_BUCKET:?CODE_BUCKET is required}"
NATIONAL_RAIL_TOKEN="${NATIONAL_RAIL_TOKEN:?NATIONAL_RAIL_TOKEN is required}"
CF_DEPLOY_API_TOKEN="${CF_DEPLOY_API_TOKEN:?CF_DEPLOY_API_TOKEN is required}"
export DOMAIN_NAME ZONE_NAME AWS_REGION STACK_NAME CODE_BUCKET NATIONAL_RAIL_TOKEN CF_DEPLOY_API_TOKEN

CERTIFICATE_ARN="$(bash "${ROOT_DIR}/scripts/request-acm-certificate.sh")"
export CERTIFICATE_ARN
bash "${ROOT_DIR}/scripts/configure-cloudflare-dns.sh"
aws acm wait certificate-validated --region us-east-1 --certificate-arn "${CERTIFICATE_ARN}"

CODE_KEY="$(bash "${ROOT_DIR}/scripts/package-lambda.sh")"
export CODE_KEY
bash "${ROOT_DIR}/scripts/deploy-stack.sh"
bash "${ROOT_DIR}/scripts/deploy-static.sh"

output() {
  aws cloudformation describe-stacks \
    --region "${AWS_REGION}" \
    --stack-name "${STACK_NAME}" \
    --query "Stacks[0].Outputs[?OutputKey=='$1'].OutputValue | [0]" \
    --output text
}

PUBLISHER_FUNCTION="$(output PublisherFunctionName)"
CLOUDFRONT_DOMAIN="$(output DistributionDomainName)"
DISTRIBUTION_ID="$(output DistributionId)"
export CLOUDFRONT_DOMAIN
aws lambda invoke --region "${AWS_REGION}" --function-name "${PUBLISHER_FUNCTION}" /tmp/led-publisher-response.json >/dev/null
bash "${ROOT_DIR}/scripts/configure-cloudflare-dns.sh"
aws cloudfront create-invalidation --distribution-id "${DISTRIBUTION_ID}" --paths '/index.html' '/api/screens' >/dev/null

echo "Deployed https://${DOMAIN_NAME}"
