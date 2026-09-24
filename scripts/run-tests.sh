#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"
export PYTHONPATH="${ROOT_DIR}/hardware/matrixportal/firmware:${ROOT_DIR}/backend:${ROOT_DIR}/shared${PYTHONPATH:+:${PYTHONPATH}}"
exec python3 -m unittest discover -s tests -v
