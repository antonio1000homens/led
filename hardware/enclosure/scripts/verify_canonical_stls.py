#!/usr/bin/env python3
"""Verify versioned canonical STLs match the meshes generated from OpenSCAD."""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

import numpy as np
import trimesh

ROOT = Path(__file__).resolve().parents[3]
PARTS_DIR = ROOT / "hardware/enclosure/parts"
PSU_DIR = ROOT / "hardware/enclosure/powersupply"
CANONICAL_DIR = ROOT / "hardware/enclosure/stl"
GENERATED_DIR = ROOT / "build/enclosure-stls"

# OpenSCAD output can contain tiny floating-point representation differences.
# Quantize coordinates at 10 nm while ignoring facet/vertex ordering.
COORD_TOLERANCE_MM = 1e-5

SOURCE_BY_STL = {
    "01_panel_hinge_template_PRINT_1.stl":
        PARTS_DIR / "01_panel_hinge_template_PRINT_1.scad",
    "02_hinged_equipment_base_PRINT_1.stl":
        PARTS_DIR / "02_hinged_equipment_base_PRINT_1.scad",
    "03_universal_equipment_backplane_PRINT_1.stl":
        PARTS_DIR / "03_universal_equipment_backplane_PRINT_1.scad",
    "04_left_equipment_side_PRINT_1.stl":
        PARTS_DIR / "04_left_equipment_side_PRINT_1.scad",
    "05_right_equipment_side_PRINT_1.stl":
        PARTS_DIR / "05_right_equipment_side_PRINT_1.scad",
    "06_psu_service_tray_snap_dock_PRINT_1.stl":
        PSU_DIR / "02_service_tray_snap_dock_PRINT_1.scad",
    "07_psu_service_tray_snap_tray_PRINT_1.stl":
        PSU_DIR / "03_service_tray_snap_tray_PRINT_1.scad",
    "08_matrixportal_s3_dock_PRINT_1.stl":
        PARTS_DIR / "08_matrixportal_s3_dock_PRINT_1.scad",
    "09_left_equipment_side_matrixportal_PRINT_1.stl":
        PARTS_DIR / "09_left_equipment_side_matrixportal_PRINT_1.scad",
    "10_matrixportal_s3_carrier_PRINT_1.stl":
        PARTS_DIR / "10_matrixportal_s3_carrier_PRINT_1.scad",
    "11_matrixportal_s3_keeper_PRINT_1.stl":
        PARTS_DIR / "11_matrixportal_s3_keeper_PRINT_1.scad",
}


def _triangle_counter(path: Path) -> Counter[tuple[tuple[int, int, int], ...]]:
    mesh = trimesh.load(path, force="mesh", process=False)
    if not isinstance(mesh, trimesh.Trimesh):
        raise ValueError(f"{path} did not load as a single triangle mesh")

    triangles = np.asarray(mesh.triangles, dtype=np.float64)
    if triangles.ndim != 3 or triangles.shape[1:] != (3, 3):
        raise ValueError(f"{path} has an unexpected triangle array shape: {triangles.shape}")

    quantized = np.rint(triangles / COORD_TOLERANCE_MM).astype(np.int64)
    return Counter(
        tuple(
            sorted(
                tuple(int(coordinate) for coordinate in vertex)
                for vertex in triangle
            )
        )
        for triangle in quantized
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--generated-dir", type=Path, default=GENERATED_DIR)
    parser.add_argument(
        "--warn-only",
        action="store_true",
        help=(
            "Report checked-in canonical STL drift as GitHub warnings instead "
            "of failing. Missing generated meshes remain fatal."
        ),
    )
    args = parser.parse_args()
    generated_dir = args.generated_dir.resolve()
    expected = set(SOURCE_BY_STL)
    canonical = {path.name for path in CANONICAL_DIR.glob("*_PRINT_1.stl")}
    generated = {path.name for path in generated_dir.glob("*_PRINT_1.stl")}

    failures: list[str] = []
    drift: list[str] = []
    drift_level = "warning" if args.warn_only else "error"

    for name in sorted(expected - canonical):
        drift.append(f"missing canonical STL: hardware/enclosure/stl/{name}")
        print(
            f"::{drift_level} file=hardware/enclosure/stl/{name}::"
            "Canonical STL is missing for an OpenSCAD print wrapper. "
            "Fresh generated geometry is available in the enclosure-stls artifact."
        )

    for name in sorted(canonical - expected):
        drift.append(f"unexpected canonical STL: hardware/enclosure/stl/{name}")
        print(
            f"::{drift_level} file=hardware/enclosure/stl/{name}::"
            "Canonical STL has no registered OpenSCAD source."
        )

    for name in sorted(expected - generated):
        source = SOURCE_BY_STL[name].relative_to(ROOT)
        failures.append(f"missing generated STL: build/enclosure-stls/{name}")
        print(
            f"::error file={source}::"
            "CI did not generate the expected STL."
        )

    for name in sorted(expected & canonical & generated):
        canonical_path = CANONICAL_DIR / name
        generated_path = generated_dir / name

        try:
            canonical_triangles = _triangle_counter(canonical_path)
            generated_triangles = _triangle_counter(generated_path)
        except Exception as exc:
            drift.append(f"{name}: mesh comparison failed: {exc}")
            print(
                f"::{drift_level} file=hardware/enclosure/stl/{name}::"
                f"Unable to compare canonical and generated STL: {exc}"
            )
            continue

        if canonical_triangles == generated_triangles:
            print(f"OK: {name} matches generated OpenSCAD geometry")
            continue

        generated_only = generated_triangles - canonical_triangles
        canonical_only = canonical_triangles - generated_triangles
        drift.append(
            f"{name}: stale geometry "
            f"({sum(generated_only.values())} generated-only triangles, "
            f"{sum(canonical_only.values())} canonical-only triangles)"
        )
        source = SOURCE_BY_STL[name].relative_to(ROOT)
        print(
            f"::{drift_level} file=hardware/enclosure/stl/{name}::"
            f"Canonical STL is stale. Regenerate it from {source} when updating "
            "the versioned manufacturing output; CI is validating the fresh "
            "generated mesh from this run."
        )

    if failures:
        print()
        print("Canonical STL verification failed:")
        for failure in failures:
            print(f"  - {failure}")
        return 1

    if drift:
        print()
        heading = (
            "Canonical STL drift warnings:"
            if args.warn_only
            else "Canonical STL verification failed:"
        )
        print(heading)
        for item in drift:
            print(f"  - {item}")
        print()
        print(
            "Fresh generated meshes are available in the enclosure-stls workflow "
            "artifact. Regenerate and commit the versioned STL outputs when "
            "manufacturing files need to be refreshed."
        )
        return 0 if args.warn_only else 1

    print()
    print(f"Canonical STL verification passed for {len(expected)} printable parts.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
