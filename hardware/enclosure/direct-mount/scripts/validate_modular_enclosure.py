#!/usr/bin/env python3
"""Validate the canonical modular hinged direct-mount enclosure."""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

import numpy as np
import trimesh
from scipy import ndimage

ROOT = Path(__file__).resolve().parents[4]
DIRECT = ROOT / "hardware/enclosure/direct-mount"
PARTS_DIR = DIRECT / "parts"
SOURCE = DIRECT / "direct_mount_enclosure.scad"
SCHEMATICS = DIRECT / "schematics"

PARTS = {
    "01_panel_hinge_template_PRINT_1.scad": "01_panel_hinge_template_PRINT_1.stl",
    "02_hinged_equipment_base_PRINT_1.scad": "02_hinged_equipment_base_PRINT_1.stl",
    "03_universal_equipment_backplane_PRINT_1.scad": "03_universal_equipment_backplane_PRINT_1.stl",
    "04_left_equipment_side_PRINT_1.scad": "04_left_equipment_side_PRINT_1.stl",
    "05_right_equipment_side_PRINT_1.scad": "05_right_equipment_side_PRINT_1.stl",
}

PREVIEWS = (
    "00_hinged_enclosure_ASSEMBLY.scad",
    "00_hinged_enclosure_CLOSED_ASSEMBLY.scad",
)

def render(source: Path, output: Path) -> None:
    completed = subprocess.run(
        ["openscad", "-o", str(output), str(source)],
        text=True,
        capture_output=True,
    )
    if completed.returncode != 0:
        raise SystemExit(
            f"OpenSCAD failed for {source.relative_to(ROOT)}:\n"
            f"{completed.stdout}\n{completed.stderr}"
        )
    if not output.is_file() or output.stat().st_size == 0:
        raise SystemExit(f"empty OpenSCAD output from {source.relative_to(ROOT)}")

def load_mesh(name: str, path: Path) -> trimesh.Trimesh:
    loaded = trimesh.load_mesh(path, process=True)
    if isinstance(loaded, trimesh.Scene):
        if not loaded.geometry:
            raise SystemExit(f"{name}: mesh scene contains no geometry")
        loaded = trimesh.util.concatenate(tuple(loaded.geometry.values()))
    if not isinstance(loaded, trimesh.Trimesh) or loaded.is_empty:
        raise SystemExit(f"{name}: could not load a non-empty mesh")
    return loaded

def assert_mesh_health(name: str, path: Path) -> None:
    mesh = load_mesh(name, path)
    if not mesh.is_watertight:
        raise SystemExit(f"{name}: generated STL is not watertight/manifold")
    components = mesh.split(only_watertight=False)
    if len(components) != 1:
        raise SystemExit(
            f"{name}: expected one connected printable shell, found {len(components)}"
        )
    if mesh.volume <= 0:
        raise SystemExit(f"{name}: generated STL has non-positive volume")
    dims = mesh.extents
    if max(dims) > 280:
        raise SystemExit(f"{name}: unexpected printable extent {dims.tolist()} mm")
    print(
        f"OK: {name} mesh health; bounds "
        f"{dims[0]:.1f} x {dims[1]:.1f} x {dims[2]:.1f} mm"
    )

def assert_no_floating_layer_islands(
    name: str,
    path: Path,
    *,
    pitch_mm: float = 1.0,
    support_radius_voxels: int = 3,
    min_component_voxels: int = 8,
) -> None:
    mesh = load_mesh(name, path)
    voxels = mesh.voxelized(pitch_mm).fill()
    matrix = np.asarray(voxels.matrix, dtype=bool)
    if matrix.ndim != 3 or not matrix.any():
        raise SystemExit(f"{name}: voxelization produced no printable volume")

    occupied_layers = np.flatnonzero(matrix.any(axis=(0, 1)))
    first_layer = int(occupied_layers[0])
    support_structure = np.ones(
        (2 * support_radius_voxels + 1, 2 * support_radius_voxels + 1),
        dtype=bool,
    )
    component_structure = np.ones((3, 3), dtype=int)

    unsupported = []
    for z_index in occupied_layers:
        z_index = int(z_index)
        if z_index <= first_layer:
            continue
        current = matrix[:, :, z_index]
        previous = matrix[:, :, z_index - 1]
        supported_xy = ndimage.binary_dilation(previous, structure=support_structure)
        labels, count = ndimage.label(current, structure=component_structure)
        for component_id in range(1, count + 1):
            component = labels == component_id
            size = int(component.sum())
            if size < min_component_voxels or np.any(component & supported_xy):
                continue
            unsupported.append((z_index, size))
            if len(unsupported) >= 5:
                break
        if len(unsupported) >= 5:
            break

    if unsupported:
        detail = ", ".join(
            f"z-index {z} ({size} voxels)" for z, size in unsupported
        )
        raise SystemExit(f"{name}: unsupported elevated slice component(s): {detail}")
    print(f"OK: {name} floating-layer proxy")

def assert_empty_intersection(work_dir: Path, name: str, body: str) -> None:
    check_scad = work_dir / f"{name}.scad"
    output = work_dir / f"{name}.stl"
    check_scad.write_text(
        f"include <{SOURCE.as_posix()}>;\n\nintersection() {{\n{body}\n}}\n",
        encoding="utf-8",
    )
    completed = subprocess.run(
        ["openscad", "-o", str(output), str(check_scad)],
        text=True,
        capture_output=True,
    )
    diagnostic = f"{completed.stdout}\n{completed.stderr}"
    if completed.returncode == 0 and output.is_file():
        raise SystemExit(f"{name}: geometry intersection has non-zero volume")
    if (
        completed.returncode != 0
        and "Current top level object is empty" not in diagnostic
    ):
        raise SystemExit(f"{name}: intersection evaluation failed:\n{diagnostic}")
    print(f"OK: {name} has no volumetric interference")

def assert_hinge_sweep(work_dir: Path) -> None:
    for angle in (0, 15, 30, 45, 60, 75, 90):
        body = f"""    hinge_mount_pattern_template();

    translate([0,hinge_axis_y,hinge_axis_z])
        rotate([{angle},0,0])
            translate([0,-hinge_axis_y,-hinge_axis_z])
                hinged_equipment_base();"""
        assert_empty_intersection(work_dir, f"hinge_sweep_{angle}", body)

def assert_no_legacy_layout() -> None:
    for path in (DIRECT / "hinge-prototype-v2", DIRECT / "hinge-version"):
        if path.exists():
            raise SystemExit(f"legacy enclosure directory still exists: {path}")
    tracked_stls = list((DIRECT / "stl").glob("*.stl"))
    if tracked_stls:
        raise SystemExit(
            "generated STL binaries must not be tracked: "
            + ", ".join(path.name for path in tracked_stls)
        )

def main() -> None:
    assert_no_legacy_layout()
    with tempfile.TemporaryDirectory(prefix="led-hinged-enclosure-") as tmp:
        work_dir = Path(tmp)
        for scad_name, stl_name in PARTS.items():
            source = PARTS_DIR / scad_name
            generated = work_dir / stl_name
            render(source, generated)
            name = source.stem
            assert_mesh_health(name, generated)
            assert_no_floating_layer_islands(name, generated)

        assert_empty_intersection(
            work_dir,
            "backplane_rail_fit",
            """    hinged_equipment_base();
    universal_equipment_backplane();""",
        )
        assert_hinge_sweep(work_dir)

        for preview in PREVIEWS:
            render(SCHEMATICS / preview, work_dir / f"{Path(preview).stem}.csg")
            print(f"OK: {preview}")

    print("All canonical hinged enclosure checks passed.")

if __name__ == "__main__":
    main()
