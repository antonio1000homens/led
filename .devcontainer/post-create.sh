#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

sudo apt-get update
sudo apt-get install -y --no-install-recommends \
  python3 python3-pip python3-venv \
  openscad curl ca-certificates xvfb xauth \
  libgl1 libglu1-mesa libosmesa6

venv_dir="${VIRTUAL_ENV:-$ROOT_DIR/.venv}"
python3 -m venv "$venv_dir"

"$venv_dir/bin/python" -m pip install --disable-pip-version-check \
  trimesh manifold3d numpy networkx scipy

cat <<'EOF_INFO'

Codespace CAD environment ready.

Fast enclosure validation:
  python3 hardware/enclosure/direct-mount/scripts/validate_enclosure.py

Remote Bambu Studio slicing is provided by Windsor Slicer. Declare models in
.windsor-slicer.yaml and use https://slicer.alf-broadcast.co.uk/mcp.

EOF_INFO
