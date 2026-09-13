#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
AWS_REGION="${AWS_REGION:-eu-west-2}"
AWS_PROFILE_NAME="${AWS_PROFILE_NAME:-${AWS_PROFILE:-}}"
STACK_NAME="${STACK_NAME:-led-bootstrap}"
CODE_BUCKET="${CODE_BUCKET:-aws2022-lambda-code-eu-west-2-553490163883}"

aws_cmd=(aws)
if [[ -n "${AWS_PROFILE_NAME}" ]]; then
  aws_cmd+=(--profile "${AWS_PROFILE_NAME}")
fi

OIDC_ARN="$(
  "${aws_cmd[@]}" iam list-open-id-connect-providers \
    --query "OpenIDConnectProviderList[?contains(Arn, 'token.actions.githubusercontent.com')].Arn | [0]" \
    --output text
)"
if [[ -z "${OIDC_ARN}" || "${OIDC_ARN}" == "None" ]]; then
  echo "No GitHub Actions OIDC provider found; creating the account-level provider." >&2
  OIDC_ARN="$(
    "${aws_cmd[@]}" iam create-open-id-connect-provider \
      --url https://token.actions.githubusercontent.com \
      --client-id-list sts.amazonaws.com \
      --thumbprint-list ffffffffffffffffffffffffffffffffffffffff \
      --query OpenIDConnectProviderArn \
      --output text
  )"
fi

"${aws_cmd[@]}" cloudformation deploy \
  --region "${AWS_REGION}" \
  --stack-name "${STACK_NAME}" \
  --template-file "${ROOT_DIR}/infrastructure/bootstrap.yaml" \
  --capabilities CAPABILITY_NAMED_IAM \
  --parameter-overrides \
    GitHubOidcProviderArn="${OIDC_ARN}" \
    ArtifactBucketName="${CODE_BUCKET}"

"${aws_cmd[@]}" cloudformation describe-stacks \
  --region "${AWS_REGION}" \
  --stack-name "${STACK_NAME}" \
  --query 'Stacks[0].Outputs' \
  --output table

echo "Set GitHub variables AWS_ROLE_TO_ASSUME and CLOUDFORMATION_ROLE_ARN from the stack outputs above." >&2
