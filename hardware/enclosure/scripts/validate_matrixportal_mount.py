#!/usr/bin/env python3
"""Validate generated MatrixPortal S3 enclosure accessory meshes."""

from __future__ import annotations

import argparse
from pathlib import Path

import trimesh

ADAPTER = "08_matrixportal_s3_adapter_PRINT_1.stl"
RIGHT_GENERIC = "05_right_equipment_side_PRINT_1.stl"
RIGHT_MATRIXPORTAL = "09_right_equipment_side_matrixportal_PRINT_1.stl"


def load_one(path: Path) -> trimesh.Trimesh:
    loaded = trimesh.load_mesh(path, process=True)
    if isinstance(loaded, trimesh.Scene):
        if not loaded.geometry:
            raise SystemExit(f"{path}: empty mesh scene")
        loaded = trimesh.util.concatenate(tuple(loaded.geometry.values()))
    if not isinstance(loaded, trimesh.Trimesh) or loaded.is_empty:
        raise SystemExit(f"{path}: empty/non-mesh STL")
    loaded.update_faces(loaded.nondegenerate_faces())
    loaded.remove_unreferenced_vertices()
    if not loaded.is_watertight:
        raise SystemExit(f"{path}: mesh is not watertight")
    if len(loaded.split(only_watertight=False)) != 1:
        raise SystemExit(f"{path}: expected one connected printable body")
    return loaded


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--generated-dir", type=Path, required=True)
    root = parser.parse_args().generated_dir.resolve()

    adapter = load_one(root / ADAPTER)
    generic = load_one(root / RIGHT_GENERIC)
    service = load_one(root / RIGHT_MATRIXPORTAL)

    dims = adapter.extents
    expected = (86.0, 55.0, 9.0)
    for actual, target in zip(dims, expected):
        if abs(float(actual)-target) > 0.25:
            raise SystemExit(
                f"{ADAPTER}: unexpected extent {dims.tolist()} mm; "
                f"expected approximately {list(expected)}"
            )

    # The MatrixPortal side must remain the same outer part envelope while
    # removing real material for the service opening.
    if max(abs(service.extents-generic.extents)) > 0.25:
        raise SystemExit(
            f"{RIGHT_MATRIXPORTAL}: outer envelope changed unexpectedly; "
            f"generic={generic.extents.tolist()} service={service.extents.tolist()}"
        )
    if not service.volume < generic.volume - 10.0:
        raise SystemExit(
            f"{RIGHT_MATRIXPORTAL}: service opening did not remove meaningful volume"
        )

    print(
        "MatrixPortal accessory validation passed: "
        f"adapter={dims.tolist()} mm, "
        f"right-side removed volume={generic.volume-service.volume:.1f} mm^3"
    )


if __name__ == "__main__":
    main()
