#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CODE_BUCKET="${CODE_BUCKET:?CODE_BUCKET is required}"
BUILD_ROOT="${BUILD_ROOT:-${ROOT_DIR}/.build}"
PACKAGE_DIR="${BUILD_ROOT}/lambda"
ZIP_FILE="${BUILD_ROOT}/led-publisher.zip"
REVISION="${GITHUB_SHA:-$(git -C "${ROOT_DIR}" rev-parse HEAD 2>/dev/null || date +%s)}"
CODE_KEY="${CODE_KEY:-led/publisher-${REVISION}.zip}"

rm -rf "${PACKAGE_DIR}" "${ZIP_FILE}"
mkdir -p "${PACKAGE_DIR}"
python3 -m pip install --disable-pip-version-check --no-compile \
  --platform manylinux2014_x86_64 --implementation cp --python-version 3.12 --abi cp312 --only-binary=:all: \
  -r "${ROOT_DIR}/requirements-server.txt" -t "${PACKAGE_DIR}" >/dev/null
cp \
  "${ROOT_DIR}/publisher.py" \
  "${ROOT_DIR}/config_api.py" \
  "${ROOT_DIR}/runtime_config.py" \
  "${ROOT_DIR}/server.py" \
  "${ROOT_DIR}/queue_times.py" \
  "${ROOT_DIR}/weather.py" \
  "${ROOT_DIR}/todoist.py" \
  "${ROOT_DIR}/fixtures.py" \
  "${PACKAGE_DIR}/"

PACKAGE_DIR="${PACKAGE_DIR}" ZIP_FILE="${ZIP_FILE}" python3 - <<'PY'
import os
from pathlib import Path
import zipfile
root=Path(os.environ["PACKAGE_DIR"]); zip_path=Path(os.environ["ZIP_FILE"])
with zipfile.ZipFile(zip_path,"w",compression=zipfile.ZIP_DEFLATED) as archive:
    for path in root.rglob("*"):
        if path.is_file(): archive.write(path,path.relative_to(root))
PY
aws s3 cp "${ZIP_FILE}" "s3://${CODE_BUCKET}/${CODE_KEY}" --only-show-errors
printf '%s\n' "${CODE_KEY}"
