#!/usr/bin/env python3
"""Generate the canonical direct-mount STL files from their OpenSCAD wrappers."""

from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DIRECT = ROOT / "hardware/enclosure"
PARTS_DIR = DIRECT / "parts"
STL_DIR = DIRECT / "stl"

PARTS = (
    "01_panel_hinge_template_PRINT_1",
    "02_hinged_equipment_base_PRINT_1",
    "03_universal_equipment_backplane_PRINT_1",
    "04_left_equipment_side_PRINT_1",
    "05_right_equipment_side_PRINT_1",
)


def main() -> None:
    STL_DIR.mkdir(parents=True, exist_ok=True)

    for stem in PARTS:
        source = PARTS_DIR / f"{stem}.scad"
        output = STL_DIR / f"{stem}.stl"
        subprocess.run(
            ["openscad", "-o", str(output), str(source)],
            check=True,
        )
        if not output.is_file() or output.stat().st_size == 0:
            raise SystemExit(f"OpenSCAD produced no output for {source}")
        print(f"generated {output.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
