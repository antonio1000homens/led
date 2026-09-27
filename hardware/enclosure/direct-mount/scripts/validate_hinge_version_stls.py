#!/usr/bin/env python3
"""Validate the modular hinge/base/backplane design introduced by issue #133.

The modular hinge STL files are generated from OpenSCAD on demand rather than
checked in as manufacturing binaries. This validator renders every printable
entrypoint, verifies basic mesh health and disconnected-shell regressions,
runs the existing coarse floating-layer proxy, and checks the two most
important installed interfaces: hinge sweep and backplane/base clearance.

Bambu Studio through windsor-slicer remains the final printability authority.
"""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

import trimesh

from validate_hinge_v2_stls import assert_no_floating_layer_islands


ROOT = Path(__file__).resolve().parents[4]
HINGE_DIR = ROOT / "hardware/enclosure/direct-mount/hinge-version"

PARTS = {
    "11_hinged_equipment_base_PRINT_1.scad":
        "11_hinged_equipment_base_PRINT_1.stl",
    "12_universal_equipment_backplane_PRINT_1.scad":
        "12_universal_equipment_backplane_PRINT_1.stl",
    "13_left_equipment_side_PRINT_1.scad":
        "13_left_equipment_side_PRINT_1.stl",
    "14_right_equipment_side_PRINT_1.scad":
        "14_right_equipment_side_PRINT_1.stl",
}

PREVIEWS = (
    "00_hinge_version_ASSEMBLY.scad",
    "00_hinge_version_CLOSED_ASSEMBLY.scad",
)


def render(source: Path, output: Path) -> None:
    subprocess.run(
        ["openscad", "-o", str(output), str(source)],
        check=True,
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
        raise SystemExit(
            f"{name}: unexpected printable extent {dims.tolist()} mm; "
            "expected every modular part to remain within 280 mm"
        )

    print(
        f"OK: {name} mesh health; bounds "
        f"{dims[0]:.1f} x {dims[1]:.1f} x {dims[2]:.1f} mm"
    )


def assert_empty_intersection(
    work_dir: Path,
    *,
    name: str,
    body: str,
) -> None:
    check_scad = work_dir / f"{name}.scad"
    intersection_stl = work_dir / f"{name}.stl"
    source = HINGE_DIR / "hinge_version.scad"

    check_scad.write_text(
        f"include <{source.as_posix()}>;\n\nintersection() {{\n{body}\n}}\n",
        encoding="utf-8",
    )

    completed = subprocess.run(
        ["openscad", "-o", str(intersection_stl), str(check_scad)],
        text=True,
        capture_output=True,
    )
    diagnostic = f"{completed.stdout}\n{completed.stderr}"

    if completed.returncode == 0 and intersection_stl.is_file():
        raise SystemExit(f"{name}: geometry intersection has non-zero volume")

    if (
        completed.returncode != 0
        and "Current top level object is empty" not in diagnostic
    ):
        raise SystemExit(f"{name}: could not evaluate intersection:\n{diagnostic}")

    print(f"OK: {name} has no volumetric interference")


def assert_hinge_sweep_clearance(work_dir: Path) -> None:
    for angle in (0, 30, 60, 90):
        body = f"""    hinge_mount_pattern_template();

    translate([0,hinge_axis_y,hinge_axis_z])
        rotate([{angle},0,0])
            translate([0,-hinge_axis_y,-hinge_axis_z])
                hinged_equipment_base();"""
        assert_empty_intersection(
            work_dir,
            name=f"modular_hinge_sweep_{angle}",
            body=body,
        )


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="led-modular-hinge-") as tmp:
        work_dir = Path(tmp)

        for scad_name, stl_name in PARTS.items():
            source = HINGE_DIR / scad_name
            generated = work_dir / stl_name
            render(source, generated)

            name = source.stem
            assert_mesh_health(name, generated)
            assert_no_floating_layer_islands(
                name,
                generated,
                pitch_mm=1.0,
                support_radius_voxels=3,
                min_component_voxels=8,
            )

        # The slide-in tongue should occupy only the designed rail clearance,
        # never intersect the hinge/base walls.
        assert_empty_intersection(
            work_dir,
            name="modular_backplane_rail_fit",
            body="""    hinged_equipment_base();
    universal_equipment_backplane();""",
        )

        assert_hinge_sweep_clearance(work_dir)

        for preview in PREVIEWS:
            source = HINGE_DIR / preview
            output = work_dir / f"{Path(preview).stem}.csg"
            render(source, output)
            print(f"OK: {preview}")

    print("All modular hinge/base/backplane geometry checks passed.")


if __name__ == "__main__":
    main()
