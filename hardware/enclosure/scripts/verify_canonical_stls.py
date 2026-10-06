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
    generated_dir = parser.parse_args().generated_dir.resolve()
    expected = set(SOURCE_BY_STL)
    canonical = {path.name for path in CANONICAL_DIR.glob("*_PRINT_1.stl")}
    generated = {path.name for path in generated_dir.glob("*_PRINT_1.stl")}

    failures: list[str] = []

    for name in sorted(expected - canonical):
        failures.append(f"missing canonical STL: hardware/enclosure/stl/{name}")
        print(
            f"::error file=hardware/enclosure/stl/{name}::"
            "Canonical STL is missing for an OpenSCAD print wrapper."
        )

    for name in sorted(canonical - expected):
        failures.append(f"unexpected canonical STL: hardware/enclosure/stl/{name}")
        print(
            f"::error file=hardware/enclosure/stl/{name}::"
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
            failures.append(f"{name}: mesh comparison failed: {exc}")
            print(
                f"::error file=hardware/enclosure/stl/{name}::"
                f"Unable to compare canonical and generated STL: {exc}"
            )
            continue

        if canonical_triangles == generated_triangles:
            print(f"OK: {name} matches generated OpenSCAD geometry")
            continue

        generated_only = generated_triangles - canonical_triangles
        canonical_only = canonical_triangles - generated_triangles
        failures.append(
            f"{name}: stale geometry "
            f"({sum(generated_only.values())} generated-only triangles, "
            f"{sum(canonical_only.values())} canonical-only triangles)"
        )
        source = SOURCE_BY_STL[name].relative_to(ROOT)
        print(
            f"::error file=hardware/enclosure/stl/{name}::"
            f"Canonical STL is stale. Regenerate it from {source} and commit "
            "the updated STL with the source change."
        )

    if failures:
        print()
        print("Canonical STL verification failed:")
        for failure in failures:
            print(f"  - {failure}")
        print()
        print(
            "Use the enclosure-stls workflow artifact as the generated reference, "
            "or regenerate the affected STL locally with OpenSCAD."
        )
        return 1

    print()
    print(f"Canonical STL verification passed for {len(expected)} printable parts.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
