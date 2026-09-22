#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"
export PYTHONPATH="${ROOT_DIR}/backend:${ROOT_DIR}/shared${PYTHONPATH:+:${PYTHONPATH}}"
exec python3 backend/server.py "$@"
