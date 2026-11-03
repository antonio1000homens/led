#!/usr/bin/env bash
set -euo pipefail

AWS_REGION="${AWS_REGION:-eu-west-2}"
PARAMETER_NAME="${R2_CREDENTIALS_PARAMETER_NAME:-/led/deploy/cloudflare/r2-s3-credentials}"
command -v aws >/dev/null || { echo 'aws CLI is required.' >&2; exit 1; }
command -v python3 >/dev/null || { echo 'python3 is required.' >&2; exit 1; }
[[ "${PARAMETER_NAME}" == /led/deploy/* ]] || { echo 'Parameter must stay under /led/deploy/.' >&2; exit 2; }

read -r -p 'R2 access key ID: ' access_key_id
read -r -s -p 'R2 secret access key: ' secret_access_key
echo
[[ -n "${access_key_id}" && -n "${secret_access_key}" ]] || { echo 'Both R2 credentials are required.' >&2; exit 2; }

temp_dir="$(mktemp -d)"
chmod 700 "${temp_dir}"
trap 'rm -rf "${temp_dir}"; unset access_key_id secret_access_key' EXIT
request_file="${temp_dir}/parameter.json"
touch "${request_file}"
chmod 600 "${request_file}"
printf '%s\0%s' "${access_key_id}" "${secret_access_key}" | python3 -c '
import json, sys
access_key_id, secret_access_key = sys.stdin.buffer.read().split(b"\0", 1)
print(json.dumps({
    "Name": sys.argv[1], "Type": "SecureString", "Tier": "Standard",
    "Overwrite": True,
    "Value": json.dumps({
        "access_key_id": access_key_id.decode(),
        "secret_access_key": secret_access_key.decode(),
    }),
}))
' "${PARAMETER_NAME}" > "${request_file}"
aws ssm put-parameter --region "${AWS_REGION}" --cli-input-json "file://${request_file}" >/dev/null
aws ssm get-parameter --region "${AWS_REGION}" --name "${PARAMETER_NAME}" \
  --query 'Parameter.[Name,Type]' --output text
unset access_key_id secret_access_key
echo 'R2 credentials stored as SecureString; values were not displayed.'
