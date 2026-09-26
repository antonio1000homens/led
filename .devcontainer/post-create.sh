#!/usr/bin/env bash
set -euo pipefail

sudo apt-get update
sudo apt-get install -y --no-install-recommends \
  python3 python3-pip python3-venv \
  openscad curl ca-certificates xvfb libgl1 libglu1-mesa

python3 -m pip install --user --disable-pip-version-check \
  trimesh manifold3d numpy networkx scipy

cat <<'EOF'

Codespace CAD environment ready.

Fast enclosure validation:
  python3 hardware/enclosure/direct-mount/scripts/validate_enclosure.py

Install the pinned Bambu Studio CLI on demand:
  bash scripts/slicer/install-bambu-studio.sh

Slice one model with the same script used by GitHub Actions:
  bash scripts/slicer/slice-stl.sh hardware/enclosure/direct-mount/hinge-prototype-v2/stl/02_middle_stationary_enclosure_HINGE_TEST.stl

To experiment with Bambu auto-orientation:
  SLICER_ORIENT=1 bash scripts/slicer/slice-stl.sh <model.stl>

EOF
