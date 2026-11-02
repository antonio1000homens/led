#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STAGE_DIR="${ROOT_DIR}/.build/matrixportal-circuitpy"
OUTPUT_DIR="${ROOT_DIR}/.build/artifacts"
ARCHIVE="${OUTPUT_DIR}/matrixportal-s3-circuitpython-app-2bit.zip"

bash "${ROOT_DIR}/scripts/stage-firmware.sh" "${STAGE_DIR}"
mkdir -p "${OUTPUT_DIR}"
rm -f "${ARCHIVE}"
(cd "${STAGE_DIR}" && zip -q -r "${ARCHIVE}" .)
printf 'Packaged MatrixPortal CircuitPython application: %s\n' "${ARCHIVE}"
