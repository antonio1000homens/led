#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TARGET="${1:-/Volumes/CIRCUITPY}"
STAGE_DIR="${ROOT_DIR}/.build/circuitpy"

if [[ ! -d "${TARGET}" ]]; then
  echo "CircuitPython target does not exist: ${TARGET}" >&2
  exit 1
fi

bash "${ROOT_DIR}/scripts/stage-firmware.sh" "${STAGE_DIR}"
cp "${STAGE_DIR}/"* "${TARGET}/"

printf 'Installed application files to %s\n' "${TARGET}"
printf 'Existing settings_local.py and lib/ contents were left untouched.\n'
