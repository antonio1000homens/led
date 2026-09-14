#!/usr/bin/env bash
set -euo pipefail

AWS_REGION="${AWS_REGION:-eu-west-2}"
SSM_PREFIX="${LED_DEPLOY_SSM_PREFIX:-/led/deploy}"

if [[ -z "${GITHUB_ENV:-}" ]]; then
  echo 'GITHUB_ENV is required; this script is intended for GitHub Actions.' >&2
  exit 1
fi

if [[ "${SSM_PREFIX}" != /* ]]; then
  echo 'LED_DEPLOY_SSM_PREFIX must start with /.' >&2
  exit 2
fi

load_parameter() {
  local env_name="$1"
  local relative_name="$2"
  local parameter_name="${SSM_PREFIX%/}/${relative_name}"
  local value
  local delimiter

  if ! value="$(aws ssm get-parameter \
      --name "${parameter_name}" \
      --with-decryption \
      --region "${AWS_REGION}" \
      --query 'Parameter.Value' \
      --output text)"; then
    echo "Unable to load required SSM parameter: ${parameter_name}" >&2
    exit 1
  fi

  if [[ -z "${value}" || "${value}" == "None" ]]; then
    echo "Required SSM parameter is empty: ${parameter_name}" >&2
    exit 1
  fi

  echo "::add-mask::${value}"
  delimiter="__SSM_${env_name}_${RANDOM}_${RANDOM}__"
  {
    echo "${env_name}<<${delimiter}"
    printf '%s\n' "${value}"
    echo "${delimiter}"
  } >> "${GITHUB_ENV}"
}

load_parameter NATIONAL_RAIL_TOKEN national-rail-token
load_parameter CF_DEPLOY_API_TOKEN cloudflare/api-token
