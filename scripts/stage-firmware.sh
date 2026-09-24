#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DESTINATION="${1:-${ROOT_DIR}/.build/circuitpy}"

rm -rf "${DESTINATION}"
mkdir -p "${DESTINATION}"

cp "${ROOT_DIR}/code.py" "${DESTINATION}/"
cp "${ROOT_DIR}/hardware/matrixportal/firmware/"*.py "${DESTINATION}/"
cp "${ROOT_DIR}/shared/"*.py "${DESTINATION}/"
cp "${ROOT_DIR}/font5x7.pcf" "${ROOT_DIR}/gtsr4.pem" "${DESTINATION}/"

printf 'Staged CircuitPython application at %s\n' "${DESTINATION}"
