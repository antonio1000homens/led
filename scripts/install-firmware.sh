#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TARGET="${1:-/Volumes/CIRCUITPY}"
STAGE_DIR="${ROOT_DIR}/.build/circuitpy"

if [[ ! -d "${TARGET}" ]]; then
  echo "CircuitPython target does not exist: ${TARGET}" >&2
  exit 1
fi

python3 - "${TARGET}/settings.toml" <<'PY'
from pathlib import Path
import re
import sys

settings = Path(sys.argv[1])
if settings.exists() and re.search(
    r'^\s*CIRCUITPY_WIFI_(SSID|PASSWORD)\s*=', settings.read_text(), re.MULTILINE
):
    raise SystemExit(
        "Rename CIRCUITPY_WIFI_SSID/PASSWORD to WIFI_SSID/PASSWORD in the board's "
        "settings.toml before installation; early automatic Wi-Fi bypasses the power limit."
    )
PY

bash "${ROOT_DIR}/scripts/stage-firmware.sh" "${STAGE_DIR}"
for source in "${STAGE_DIR}/"*; do
  if [[ "$(basename "${source}")" != "code.py" ]]; then
    cp "${source}" "${TARGET}/"
  fi
done
cp "${STAGE_DIR}/code.py" "${TARGET}/code.py"

printf 'Installed application files to %s\n' "${TARGET}"
printf 'Existing settings_local.py and lib/ contents were left untouched.\n'
printf 'Power-cycle the board to apply boot.py. Automatic browser maintenance is disabled.\n'
