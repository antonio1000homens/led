#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
AWS_REGION="${AWS_REGION:-eu-west-2}"
STACK_NAME="${STACK_NAME:-led-serverless}"
output(){ aws cloudformation describe-stacks --region "${AWS_REGION}" --stack-name "${STACK_NAME}" --query "Stacks[0].Outputs[?OutputKey=='$1'].OutputValue | [0]" --output text; }
BUCKET="$(output HostingBucketName)"; DISTRIBUTION_ID="$(output DistributionId)"
aws s3 cp "${ROOT_DIR}/simulator/index.html" "s3://${BUCKET}/index.html" --content-type text/html --cache-control 'public, max-age=300' --only-show-errors
aws s3 cp "${ROOT_DIR}/simulator/admin.html" "s3://${BUCKET}/admin.html" --content-type text/html --cache-control 'no-store' --only-show-errors
aws cloudfront create-invalidation --distribution-id "${DISTRIBUTION_ID}" --paths '/index.html' '/api/screens' >/dev/null
aws cloudfront create-invalidation --distribution-id "${DISTRIBUTION_ID}" --paths '/admin.html' '/api/config' >/dev/null
