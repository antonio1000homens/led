#!/usr/bin/env python3
"""Run the complete direct-mount enclosure validation suite.

This script is the single CI entrypoint for enclosure/mechanical validation.
It intentionally renders each current production STL once from its printable
wrapper entrypoint, compares that mesh with the checked-in manufacturing STL,
then runs assembly, hinge-v2, and experimental hinge-version checks.
"""

from __future__ import annotations

import hashlib
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
DIRECT = ROOT / "hardware/enclosure/direct-mount"
PARTS_DIR = DIRECT / "parts"
STL_DIR = DIRECT / "stl"
SCRIPTS_DIR = DIRECT / "scripts"
SCHEMATICS_DIR = DIRECT / "schematics"
ASSEMBLY_DIR = ROOT / "hardware/enclosure/complete_enclosure"
HINGE_DIR = DIRECT / "hinge-version"
HINGE_PARTS = {
    "08_mount_pattern_template_HINGE_PRINT_1.scad":
        "08_mount_pattern_template_HINGE_PRINT_1.stl",
    "11_hinged_equipment_enclosure_PRINT_1.scad":
        "11_hinged_equipment_enclosure_PRINT_1.stl",
}

PARTS = {
    "01_backplane_module_PRINT_3.scad": "01_backplane_module_PRINT_3.stl",
    "01b_backplane_right_end_PRINT_1.scad": "01b_backplane_right_end_PRINT_1.stl",
    "02_module_joiner_PRINT_4.scad": "02_module_joiner_PRINT_4.stl",
    "03_rod_end_plug_PRINT_4.scad": "03_rod_end_plug_PRINT_4.stl",
    "04_matrixportal_mount_PRINT_1.scad": "04_matrixportal_mount_PRINT_1.stl",
    "05_power_distribution_mount_PRINT_1.scad": "05_power_distribution_mount_PRINT_1.stl",
    "06_cable_clip_PRINT_8.scad": "06_cable_clip_PRINT_8.stl",
    "07_mounting_slot_coupon_PRINT_1.scad": "07_mounting_slot_coupon_PRINT_1.stl",
    "08_mount_pattern_template_PRINT_1.scad": "08_mount_pattern_template_PRINT_1.stl",
    "09_centre_boss_desk_stand_PRINT_3.scad": "09_centre_boss_desk_stand_PRINT_3.stl",
    "10_rear_lid_PRINT_4.scad": "10_rear_lid_PRINT_4.stl",
}

CSG_PREVIEWS = {
    SCHEMATICS_DIR / "04_matrixportal_side_access_ASSEMBLY.scad":
        "matrixportal_side_access_preview.csg",
    SCHEMATICS_DIR / "10_rear_lid_alignment_ASSEMBLY.scad":
        "rear_lid_alignment_preview.csg",
    ASSEMBLY_DIR / "00_complete_enclosure_ASSEMBLY.scad":
        "complete_enclosure_assembly.csg",
}

SVG_VIEWS = (
    "00_complete_enclosure_FRONT_VIEW_SVG.scad",
    "00_complete_enclosure_BACK_VIEW_SVG.scad",
    "00_complete_enclosure_LEFT_SIDE_VIEW_SVG.scad",
    "00_complete_enclosure_RIGHT_SIDE_VIEW_SVG.scad",
    "00_complete_enclosure_TOP_VIEW_SVG.scad",
    "00_complete_enclosure_BOTTOM_VIEW_SVG.scad",
)


def run(*args: str | Path) -> None:
    command = [str(arg) for arg in args]
    print("+", " ".join(command), flush=True)
    subprocess.run(command, check=True)


def canonical_hash(path: Path) -> str:
    triangles = []
    vertices = []

    with path.open(encoding="utf-8", errors="strict") as handle:
        for raw in handle:
            line = raw.strip()
            if not line.startswith("vertex "):
                continue
            _, xs, ys, zs = line.split()
            vertex = tuple(round(float(value), 6) for value in (xs, ys, zs))
            vertices.append(vertex)
            if len(vertices) == 3:
                triangles.append(tuple(sorted(vertices)))
                vertices = []

    if vertices:
        raise RuntimeError(f"incomplete triangle data in {path}")

    payload = repr(sorted(triangles)).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def reject_superseded_backplane() -> None:
    # Build the old filename dynamically so this validator does not flag itself.
    needle = "01_backplane_module_" + "PRINT_4"
    allowed_suffixes = {".scad", ".md", ".py", ".json"}

    matches = []
    for path in DIRECT.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in allowed_suffixes:
            continue
        if path.resolve() == Path(__file__).resolve():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if needle in text:
            matches.append(path.relative_to(ROOT))

    if matches:
        formatted = "\n".join(f"  - {path}" for path in matches)
        raise SystemExit(
            "Superseded PRINT_4 backplane reference found. "
            "Use PRINT_3 plus the right-end variant:\n"
            f"{formatted}"
        )

    print("OK: no superseded PRINT_4 backplane references")


def validate_production_parts(generated_dir: Path) -> None:
    expected = sorted(PARTS.values())
    actual = sorted(path.name for path in STL_DIR.glob("*.stl"))

    if actual != expected:
        missing = sorted(set(expected) - set(actual))
        extra = sorted(set(actual) - set(expected))
        raise SystemExit(
            "Checked-in STL file set does not match printable entrypoints. "
            f"missing={missing}, extra={extra}"
        )

    for scad_name, stl_name in PARTS.items():
        source = PARTS_DIR / scad_name
        generated = generated_dir / stl_name
        tracked = STL_DIR / stl_name

        run("openscad", "-o", generated, source)

        if canonical_hash(generated) != canonical_hash(tracked):
            raise SystemExit(
                f"STALE: {tracked.relative_to(ROOT)}\n"
                f"Regenerate it from {source.relative_to(ROOT)}."
            )

        print(f"OK: {source.name} -> {tracked.name}")

    run(
        sys.executable,
        SCRIPTS_DIR / "validate_matrixportal_stl.py",
        generated_dir / "04_matrixportal_mount_PRINT_1.stl",
    )


def validate_reference_views(generated_dir: Path) -> None:
    for source, output_name in CSG_PREVIEWS.items():
        run("openscad", "-o", generated_dir / output_name, source)

    for view in SVG_VIEWS:
        source = ASSEMBLY_DIR / view
        output = generated_dir / f"{source.stem}.svg"
        run("openscad", "-o", output, source)

        if not output.is_file() or output.stat().st_size == 0:
            raise SystemExit(f"empty SVG output from {source.relative_to(ROOT)}")
        if "<svg" not in output.read_text(encoding="utf-8", errors="ignore"):
            raise SystemExit(f"invalid SVG output from {source.relative_to(ROOT)}")
        print(f"OK: {source.name} -> SVG")


def validate_hinge_v2() -> None:
    run(sys.executable, SCRIPTS_DIR / "validate_hinge_v2_stls.py")


def validate_hinge_print_orientation(mesh: Path) -> None:
    import math
    from collections import defaultdict

    triangles = []
    tri = []
    mins = [float("inf")] * 3
    maxs = [float("-inf")] * 3

    with mesh.open(encoding="utf-8", errors="strict") as handle:
        for raw in handle:
            line = raw.strip()
            if not line.startswith("vertex "):
                continue
            _, xs, ys, zs = line.split()
            vertex = tuple(float(value) for value in (xs, ys, zs))
            for axis, value in enumerate(vertex):
                mins[axis] = min(mins[axis], value)
                maxs[axis] = max(maxs[axis], value)
            tri.append(vertex)
            if len(tri) == 3:
                triangles.append(tuple(tri))
                tri = []

    if tri or not triangles:
        raise SystemExit(f"invalid or empty hinge STL: {mesh}")

    dims = tuple(maxs[i] - mins[i] for i in range(3))
    expected = (57.4, 127.0, 255.0)
    if any(abs(actual - target) > 0.25 for actual, target in zip(dims, expected)):
        raise SystemExit(
            f"moving enclosure is no longer in side-print orientation: "
            f"dimensions={dims}, expected~={expected}"
        )
    if abs(mins[2]) > 0.05:
        raise SystemExit(f"moving enclosure does not sit on print Z=0: min_z={mins[2]}")

    def sub(a, b):
        return tuple(a[i] - b[i] for i in range(3))

    def cross(a, b):
        return (
            a[1] * b[2] - a[2] * b[1],
            a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0],
        )

    downward_by_z = defaultdict(float)
    for a, b, c in triangles:
        normal = cross(sub(b, a), sub(c, a))
        magnitude = math.sqrt(sum(value * value for value in normal))
        if not magnitude:
            continue
        if normal[2] / magnitude < -0.9999:
            z = round((a[2] + b[2] + c[2]) / 3.0, 3)
            if z > 0.05:
                downward_by_z[z] += magnitude / 2.0

    largest = max(downward_by_z.values(), default=0.0)
    if largest > 1000.0:
        raise SystemExit(
            "moving enclosure has a large downward horizontal start surface: "
            f"{largest:.1f} mm^2 (limit 1000 mm^2)"
        )
    print(
        "OK: moving enclosure print orientation "
        f"{dims[0]:.1f} x {dims[1]:.1f} x {dims[2]:.1f} mm; "
        f"largest elevated downward-horizontal surface {largest:.1f} mm^2"
    )


def validate_hinge_prototype(generated_dir: Path) -> None:
    tracked_dir = HINGE_DIR / "stl"
    for scad_name, stl_name in HINGE_PARTS.items():
        source = HINGE_DIR / scad_name
        generated = generated_dir / stl_name
        tracked = tracked_dir / stl_name
        run("openscad", "-o", generated, source)
        if canonical_hash(generated) != canonical_hash(tracked):
            raise SystemExit(
                f"STALE: {tracked.relative_to(ROOT)}\n"
                f"Regenerate it from {source.relative_to(ROOT)}."
            )
        print(f"OK: hinge-version/{source.name} -> stl/{tracked.name}")
        if scad_name == "11_hinged_equipment_enclosure_PRINT_1.scad":
            validate_hinge_print_orientation(generated)

    run("openscad", "-o", generated_dir / "hinge_version_assembly.csg",
        HINGE_DIR / "00_hinge_version_ASSEMBLY.scad")
    run("openscad", "-o", generated_dir / "hinge_version_closed_assembly.csg",
        HINGE_DIR / "00_hinge_version_CLOSED_ASSEMBLY.scad")


def validate_nominal_assembly() -> None:
    run(
        sys.executable,
        SCRIPTS_DIR / "validate_assembly.py",
        SCRIPTS_DIR / "assembly_validation.json",
    )


def main() -> None:
    reject_superseded_backplane()

    with tempfile.TemporaryDirectory(prefix="led-enclosure-") as tmp:
        generated_dir = Path(tmp)
        validate_production_parts(generated_dir)
        validate_reference_views(generated_dir)
        validate_hinge_prototype(generated_dir)

    validate_hinge_v2()
    validate_nominal_assembly()

    print()
    print("All current enclosure validation checks passed.")
    print("Experimental hinge-version meshes and assembly syntax passed validation.")
    print(
        "Bambu Studio remains the final authority for slicer-specific support "
        "and floating-cantilever diagnostics."
    )


if __name__ == "__main__":
    main()
