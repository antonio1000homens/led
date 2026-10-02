#!/usr/bin/env python3
"""Generate the canonical enclosure STL files from their OpenSCAD wrappers."""

from __future__ import annotations

import subprocess
import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DIRECT = ROOT / "hardware/enclosure"
STL_DIR = DIRECT / "stl"

OUTPUTS = (
    (
        DIRECT / "parts/01_panel_hinge_template_PRINT_1.scad",
        "01_panel_hinge_template_PRINT_1.stl",
    ),
    (
        DIRECT / "parts/02_hinged_equipment_base_PRINT_1.scad",
        "02_hinged_equipment_base_PRINT_1.stl",
    ),
    (
        DIRECT / "parts/03_universal_equipment_backplane_PRINT_1.scad",
        "03_universal_equipment_backplane_PRINT_1.stl",
    ),
    (
        DIRECT / "parts/04_left_equipment_side_PRINT_1.scad",
        "04_left_equipment_side_PRINT_1.stl",
    ),
    (
        DIRECT / "parts/05_right_equipment_side_PRINT_1.scad",
        "05_right_equipment_side_PRINT_1.stl",
    ),
    (
        DIRECT / "powersupply/02_service_tray_snap_dock_PRINT_1.scad",
        "06_psu_service_tray_snap_dock_PRINT_1.stl",
    ),
    (
        DIRECT / "powersupply/03_service_tray_snap_tray_PRINT_1.scad",
        "07_psu_service_tray_snap_tray_PRINT_1.stl",
    ),
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=STL_DIR,
        help="Output directory (defaults to the checked-in canonical STL directory).",
    )
    output_dir = parser.parse_args().output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    for source, output_name in OUTPUTS:
        output = output_dir / output_name
        subprocess.run(
            ["openscad", "-o", str(output), str(source)],
            check=True,
        )
        if not output.is_file() or output.stat().st_size == 0:
            raise SystemExit(f"OpenSCAD produced no output for {source}")
        try:
            label = output.relative_to(ROOT)
        except ValueError:
            label = output
        print(f"generated {label}")


if __name__ == "__main__":
    main()
