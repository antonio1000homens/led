#!/usr/bin/env python3
"""Validate generated MatrixPortal S3 side-dock/carrier enclosure meshes."""

from __future__ import annotations

import argparse
from pathlib import Path

import trimesh

DOCK = "08_matrixportal_s3_dock_PRINT_1.stl"
LEFT_GENERIC = "04_left_equipment_side_PRINT_1.stl"
LEFT_MATRIXPORTAL = "09_left_equipment_side_matrixportal_PRINT_1.stl"
CARRIER = "10_matrixportal_s3_carrier_PRINT_1.stl"
KEEPER = "11_matrixportal_s3_keeper_PRINT_1.stl"


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


def check_extents(name: str, mesh: trimesh.Trimesh, expected: tuple[float, ...]) -> None:
    dims = mesh.extents
    for actual, target in zip(dims, expected):
        if abs(float(actual)-target) > 0.25:
            raise SystemExit(
                f"{name}: unexpected extent {dims.tolist()} mm; "
                f"expected approximately {list(expected)}"
            )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--generated-dir", type=Path, required=True)
    root = parser.parse_args().generated_dir.resolve()

    dock = load_one(root / DOCK)
    carrier = load_one(root / CARRIER)
    keeper = load_one(root / KEEPER)
    generic = load_one(root / LEFT_GENERIC)
    service = load_one(root / LEFT_MATRIXPORTAL)

    # Side-mount ears extend 5 mm beyond each Y edge of the original 50 mm dock.\n    check_extents(DOCK, dock, (86.0, 60.0, 6.8))
    check_extents(CARRIER, carrier, (85.0, 50.0, 22.2))
    check_extents(KEEPER, keeper, (6.5, 26.685, 6.15))

    # The dedicated side now carries two small inward receiver channels.
    # They may add up to ~0.6 mm to the generic inner-depth envelope, but must
    # not alter the visible Y/Z end-cap silhouette.
    delta = abs(service.extents-generic.extents)
    if float(delta.max()) > 1.0:
        raise SystemExit(
            f"{LEFT_MATRIXPORTAL}: side-dock receivers changed the outer envelope too much; "
            f"generic={generic.extents.tolist()} service={service.extents.tolist()}"
        )
    if not service.volume < generic.volume - 10.0:
        raise SystemExit(
            f"{LEFT_MATRIXPORTAL}: service opening did not remove meaningful volume"
        )

    # The removable carrier should remain materially smaller than the dock in X
    # so its leading edge can seat against the independent fixed stop.
    if not carrier.extents[0] <= dock.extents[0] - 0.5:
        raise SystemExit(
            "MatrixPortal carrier is too long to retain an independent dock stop"
        )

    print(
        "MatrixPortal side-mounted click-dock validation passed: "
        f"dock={dock.extents.tolist()} mm, "
        f"carrier={carrier.extents.tolist()} mm, "
        f"keeper={keeper.extents.tolist()} mm, "
        f"left-side removed volume={generic.volume-service.volume:.1f} mm^3"
    )


if __name__ == "__main__":
    main()
