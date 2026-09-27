#!/usr/bin/env python3
"""Single CI entrypoint for the canonical hinged enclosure."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "hardware/enclosure/direct-mount/scripts/validate_modular_enclosure.py"

def main() -> None:
    subprocess.run([sys.executable, str(SCRIPT)], check=True)
    print()
    print("Canonical hinged direct-mount enclosure validation passed.")
    print("Use Windsor Slicer/Bambu Studio for the final H2D printability gate.")

if __name__ == "__main__":
    main()
