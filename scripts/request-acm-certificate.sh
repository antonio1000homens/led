#!/usr/bin/env bash
set -euo pipefail

DOMAIN_NAME="${DOMAIN_NAME:-led.alf-broadcast.co.uk}"
ACM_REGION="${ACM_REGION:-us-east-1}"
AWS_PROFILE_NAME="${AWS_PROFILE_NAME:-${AWS_PROFILE:-}}"

aws_cmd=(aws)
if [[ -n "${AWS_PROFILE_NAME}" ]]; then
  aws_cmd+=(--profile "${AWS_PROFILE_NAME}")
fi

CERTIFICATE_ARN="$(
  "${aws_cmd[@]}" acm list-certificates \
    --region "${ACM_REGION}" \
    --certificate-statuses PENDING_VALIDATION ISSUED \
    --query "CertificateSummaryList[?DomainName=='${DOMAIN_NAME}'].CertificateArn | [0]" \
    --output text
)"

if [[ -z "${CERTIFICATE_ARN}" || "${CERTIFICATE_ARN}" == "None" ]]; then
  echo "Requesting ACM certificate for ${DOMAIN_NAME} in ${ACM_REGION}." >&2
  CERTIFICATE_ARN="$(
    "${aws_cmd[@]}" acm request-certificate \
      --region "${ACM_REGION}" \
      --domain-name "${DOMAIN_NAME}" \
      --validation-method DNS \
      --idempotency-token ledalfbroadcast2026 \
      --options CertificateTransparencyLoggingPreference=ENABLED \
      --query CertificateArn \
      --output text
  )"
  for _ in {1..12}; do
    name="$("${aws_cmd[@]}" acm describe-certificate --region "${ACM_REGION}" --certificate-arn "${CERTIFICATE_ARN}" --query 'Certificate.DomainValidationOptions[0].ResourceRecord.Name' --output text 2>/dev/null || true)"
    [[ -n "${name}" && "${name}" != "None" ]] && break
    sleep 5
  done
else
  echo "Reusing ACM certificate for ${DOMAIN_NAME}." >&2
fi

printf '%s\n' "${CERTIFICATE_ARN}"
