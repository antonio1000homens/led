#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "${script_dir}/.." && pwd)"
default_config_file="${repo_root}/config/bootstrap-ssm-migration.env"
CONFIG_FILE="${BOOTSTRAP_CONFIG:-${default_config_file}}"
config_explicit=false

args=("$@")
for ((i = 0; i < ${#args[@]}; i++)); do
  if [[ "${args[$i]}" == "--config" ]]; then
    if ((i + 1 >= ${#args[@]})); then
      echo '--config requires a value.' >&2
      exit 2
    fi
    CONFIG_FILE="${args[$((i + 1))]}"
    config_explicit=true
    ((i += 1))
  fi
done

if [[ -f "${CONFIG_FILE}" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "${CONFIG_FILE}"
  set +a
elif [[ "${config_explicit}" == "true" ]]; then
  echo "Configuration file not found: ${CONFIG_FILE}" >&2
  exit 1
fi

REPO="${REPO:-antonio1000homens/led}"
GH_ENVIRONMENT="${GH_ENVIRONMENT:-}"
AWS_REGION="${AWS_REGION:-eu-west-2}"
STACK_NAME="${STACK_NAME:-led-bootstrap}"
DEPLOYMENT_ROLE_NAME="${DEPLOYMENT_ROLE_NAME:-GitHubActionsLedDeployRole}"
SSM_PREFIX="${SSM_PREFIX:-/led/deploy}"
DRY_RUN=false

usage() {
  cat <<EOF
Usage: scripts/bootstrap-ssm-migration.sh [options]

Migrate or refresh LED deployment-time secrets from Bitwarden Secrets Manager
into AWS SSM Parameter Store. GitHub Actions consumes SSM after assuming the
existing GitHubActionsLedDeployRole through OIDC.

By default the script loads local configuration from:
  ${default_config_file}

Copy config/bootstrap-ssm-migration.env.example to that path and fill in any
local authentication/profile settings or Bitwarden secret-ID overrides. The
populated file is gitignored.

Prerequisites:
  - aws CLI authenticated to the target AWS account
  - gh CLI authenticated with access to antonio1000homens/led
  - bws CLI authenticated to the LED Bitwarden project
  - jq

Options:
  --config FILE              Load a different local configuration file
  --repo OWNER/REPO          GitHub repository (default: antonio1000homens/led)
  --environment NAME         Optional GitHub Actions environment for variables
  --region REGION            AWS region (default: eu-west-2)
  --ssm-prefix PATH          Deployment-only SSM path (default: /led/deploy)
  --stack-name NAME          Bootstrap CloudFormation stack (default: led-bootstrap)
  --role-name NAME           Existing GitHub OIDC deploy role name
  --dry-run                  Validate authentication and mapping without changes
  -h, --help                 Show this help

Configuration precedence:
  CLI argument > config file/environment variable > built-in default.

Bitwarden mapping:
  The script discovers secrets by logical key where possible. If discovery is
  ambiguous or the key differs, set the existing Bitwarden secret UUID in:

    BW_NATIONAL_RAIL_TOKEN
    BW_CF_DEPLOY_API_TOKEN

These variables are Bitwarden secret IDs, never secret values.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --config)
      shift 2
      ;;
    --repo)
      REPO="${2:?--repo requires a value}"
      shift 2
      ;;
    --environment)
      GH_ENVIRONMENT="${2:?--environment requires a value}"
      shift 2
      ;;
    --region)
      AWS_REGION="${2:?--region requires a value}"
      shift 2
      ;;
    --ssm-prefix)
      SSM_PREFIX="${2:?--ssm-prefix requires a value}"
      shift 2
      ;;
    --stack-name)
      STACK_NAME="${2:?--stack-name requires a value}"
      shift 2
      ;;
    --role-name)
      DEPLOYMENT_ROLE_NAME="${2:?--role-name requires a value}"
      shift 2
      ;;
    --dry-run)
      DRY_RUN=true
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

for command_name in aws gh bws jq; do
  command -v "${command_name}" >/dev/null 2>&1 || {
    echo "Required command not found: ${command_name}" >&2
    exit 1
  }
done

if [[ "${SSM_PREFIX}" != /* ]]; then
  echo 'SSM_PREFIX must start with /.' >&2
  exit 2
fi

SSM_PREFIX="${SSM_PREFIX%/}"
if [[ "${SSM_PREFIX}" != "/led/deploy" && "${SSM_PREFIX}" != /led/deploy/* ]]; then
  echo 'SSM_PREFIX must remain within /led/deploy because the GitHub deploy role is scoped to that hierarchy.' >&2
  exit 2
fi

printf 'Checking AWS authentication... '
AWS_ACCOUNT_ID="$(aws sts get-caller-identity --query Account --output text --region "${AWS_REGION}")"
[[ -n "${AWS_ACCOUNT_ID}" && "${AWS_ACCOUNT_ID}" != "None" ]] || {
  echo 'Unable to resolve AWS account ID.' >&2
  exit 1
}
echo "account ${AWS_ACCOUNT_ID}"

printf 'Validating bootstrap template... '
aws cloudformation validate-template \
  --region "${AWS_REGION}" \
  --template-body "file://${repo_root}/infrastructure/bootstrap.yaml" \
  >/dev/null
echo 'ok'

printf 'Checking GitHub authentication... '
gh auth status >/dev/null
GH_REPO="$(gh repo view "${REPO}" --json nameWithOwner --jq .nameWithOwner)"
[[ "${GH_REPO}" == "${REPO}" ]] || {
  echo "Authenticated GitHub account cannot resolve ${REPO}." >&2
  exit 1
}
echo "${GH_REPO}"

printf 'Checking Bitwarden Secrets Manager authentication... '
BITWARDEN_CATALOG="$(bws secret list --output json | jq -ce '[.[] | {id, key}]')"
echo 'ok'

resolve_secret_id() {
  local override_name="$1"
  shift
  local override_value="${!override_name:-}"
  local key
  local match
  local matches=()

  if [[ -n "${override_value}" ]]; then
    if ! jq -e --arg id "${override_value}" 'any(.[]; .id == $id)' <<<"${BITWARDEN_CATALOG}" >/dev/null; then
      echo "${override_name} does not match a secret visible to the current bws session." >&2
      return 1
    fi
    printf '%s' "${override_value}"
    return 0
  fi

  for key in "$@"; do
    while IFS= read -r match; do
      [[ -n "${match}" ]] && matches+=("${match}")
    done < <(jq -r --arg key "${key}" '.[] | select(.key == $key) | .id' <<<"${BITWARDEN_CATALOG}")
  done

  if [[ ${#matches[@]} -eq 1 ]]; then
    printf '%s' "${matches[0]}"
    return 0
  fi

  if [[ ${#matches[@]} -eq 0 ]]; then
    echo "Unable to find Bitwarden secret for ${override_name}." >&2
  else
    echo "Multiple Bitwarden secrets matched ${override_name}; refusing to guess." >&2
  fi
  echo "Set ${override_name}=<secret-uuid> in the local config file or environment." >&2
  return 1
}

BW_RAIL_ID="$(resolve_secret_id BW_NATIONAL_RAIL_TOKEN NATIONAL_RAIL_TOKEN)"
BW_CF_ID="$(resolve_secret_id BW_CF_DEPLOY_API_TOKEN CF_DEPLOY_API_TOKEN CLOUDFLARE_API_TOKEN)"

echo 'Resolved both Bitwarden secret IDs without reading or printing secret values.'
echo "AWS region: ${AWS_REGION}"
echo "SSM prefix: ${SSM_PREFIX}"
echo "Bootstrap stack: ${STACK_NAME}"
echo "GitHub repository: ${REPO}"
if [[ -n "${GH_ENVIRONMENT}" ]]; then
  echo "GitHub environment: ${GH_ENVIRONMENT}"
else
  echo 'GitHub variables: repository-level'
fi
if [[ -f "${CONFIG_FILE}" ]]; then
  echo "Local config: ${CONFIG_FILE}"
fi

if [[ "${DRY_RUN}" == "true" ]]; then
  echo 'Dry run complete; no AWS, SSM or GitHub changes were made.'
  exit 0
fi

echo 'Updating the existing LED bootstrap stack with scoped SSM read access...'
AWS_REGION="${AWS_REGION}" \
STACK_NAME="${STACK_NAME}" \
AWS_PROFILE_NAME="${AWS_PROFILE_NAME:-${AWS_PROFILE:-}}" \
  bash "${repo_root}/scripts/bootstrap-deployment-role.sh" >/dev/null

ROLE_ARN="$(aws cloudformation describe-stacks \
  --region "${AWS_REGION}" \
  --stack-name "${STACK_NAME}" \
  --query "Stacks[0].Outputs[?OutputKey=='AwsRoleToAssume'].OutputValue | [0]" \
  --output text)"
CLOUDFORMATION_ROLE_ARN="$(aws cloudformation describe-stacks \
  --region "${AWS_REGION}" \
  --stack-name "${STACK_NAME}" \
  --query "Stacks[0].Outputs[?OutputKey=='CloudFormationRoleArn'].OutputValue | [0]" \
  --output text)"

[[ -n "${ROLE_ARN}" && "${ROLE_ARN}" != "None" ]] || {
  echo 'Bootstrap stack did not return AwsRoleToAssume.' >&2
  exit 1
}
[[ -n "${CLOUDFORMATION_ROLE_ARN}" && "${CLOUDFORMATION_ROLE_ARN}" != "None" ]] || {
  echo 'Bootstrap stack did not return CloudFormationRoleArn.' >&2
  exit 1
}

secret_request_dir="$(mktemp -d)"
chmod 700 "${secret_request_dir}"
trap 'rm -rf "${secret_request_dir}"' EXIT

put_secret_parameter() {
  local relative_name="$1"
  local secret_id="$2"
  local parameter_name="${SSM_PREFIX}/${relative_name}"
  local value
  local request_file

  value="$(bws secret get "${secret_id}" --output json | jq -er '.value')"
  if [[ -z "${value}" ]]; then
    echo "Bitwarden secret ${secret_id} returned an empty value; refusing to write ${parameter_name}." >&2
    exit 1
  fi

  request_file="$(mktemp "${secret_request_dir}/put-parameter.XXXXXX")"
  chmod 600 "${request_file}"
  printf '%s' "${value}" | jq -Rs \
    --arg name "${parameter_name}" \
    '{Name:$name, Type:"SecureString", Tier:"Standard", Value:., Overwrite:true}' \
    > "${request_file}"

  aws ssm put-parameter \
    --region "${AWS_REGION}" \
    --cli-input-json "file://${request_file}" \
    >/dev/null

  rm -f "${request_file}"
  unset value
  echo "Stored ${parameter_name} as Standard SecureString"
}

put_secret_parameter national-rail-token "${BW_RAIL_ID}"
put_secret_parameter cloudflare/api-token "${BW_CF_ID}"

echo 'Validating SSM parameter names and types without decrypting values...'
for relative_name in national-rail-token cloudflare/api-token; do
  parameter_name="${SSM_PREFIX}/${relative_name}"
  read -r found_name found_type <<<"$(aws ssm get-parameter \
    --name "${parameter_name}" \
    --region "${AWS_REGION}" \
    --query 'Parameter.[Name,Type]' \
    --output text)"
  [[ "${found_name}" == "${parameter_name}" && "${found_type}" == "SecureString" ]] || {
    echo "Unable to validate ${parameter_name} as SecureString." >&2
    exit 1
  }
done

echo 'Writing non-secret GitHub Actions variables...'
set_gh_variable() {
  local name="$1"
  local value="$2"
  local gh_args=(--repo "${REPO}")
  if [[ -n "${GH_ENVIRONMENT}" ]]; then
    gh_args+=(--env "${GH_ENVIRONMENT}")
  fi
  gh variable set "${name}" "${gh_args[@]}" --body "${value}"
}

set_gh_variable AWS_ROLE_TO_ASSUME "${ROLE_ARN}"
set_gh_variable CLOUDFORMATION_ROLE_ARN "${CLOUDFORMATION_ROLE_ARN}"
set_gh_variable LED_DEPLOY_SSM_PREFIX "${SSM_PREFIX}"

echo 'Bootstrap complete. No secret values were written to GitHub.'
echo 'Run the production deployment workflow, validate rail/Cloudflare/Todoist behaviour, then remove stale Bitwarden GitHub settings.'
