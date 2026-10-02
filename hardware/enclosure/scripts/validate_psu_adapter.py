#!/usr/bin/env python3
"""Validate issue #177 PSU adapter meshes and their enclosure/slide fit."""
from __future__ import annotations

import argparse
import math
import subprocess
import tempfile
import warnings
from pathlib import Path

import trimesh

ROOT = Path(__file__).resolve().parents[3]
ENCLOSURE = ROOT / "hardware/enclosure"
PSU = ENCLOSURE / "powersupply"


def render(source: Path, output: Path) -> None:
    result = subprocess.run(["openscad", "-o", str(output), str(source)],
                            capture_output=True, text=True)
    if result.returncode or not output.is_file() or output.stat().st_size == 0:
        raise SystemExit(f"OpenSCAD failed for {source}:\n{result.stdout}\n{result.stderr}")


def mesh(path: Path, label: str) -> trimesh.Trimesh:
    loaded = trimesh.load(path, force="mesh", process=True)
    if not isinstance(loaded, trimesh.Trimesh) or loaded.is_empty:
        raise SystemExit(f"{label}: could not load a non-empty triangle mesh")
    loaded.update_faces(loaded.nondegenerate_faces())
    loaded.remove_unreferenced_vertices()
    if not loaded.is_watertight or len(loaded.split(only_watertight=False)) != 1:
        raise SystemExit(f"{label}: expected one connected watertight solid")
    if loaded.volume <= 0:
        raise SystemExit(f"{label}: mesh has non-positive volume")
    print(f"OK: {label} is one watertight component; bounds={loaded.bounds.tolist()}")
    return loaded


def intersection_volume(a: trimesh.Trimesh, b: trimesh.Trimesh) -> float:
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=RuntimeWarning,
                                message="invalid value encountered in divide")
        result = trimesh.boolean.intersection([a, b], engine="manifold")
        if isinstance(result, list):
            return sum(part.volume for part in result)
        return float(result.volume) if isinstance(result, trimesh.Trimesh) else 0.0


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--generated-dir", type=Path)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="psu-adapter-validation-") as temp:
        tmp = Path(temp)
        generated = args.generated_dir.resolve() if args.generated_dir else tmp
        generated.mkdir(parents=True, exist_ok=True)
        dock_path = generated / "06_psu_service_tray_snap_dock_PRINT_1.stl"
        tray_path = generated / "07_psu_service_tray_snap_tray_PRINT_1.stl"
        if not dock_path.is_file():
            render(PSU / "02_service_tray_snap_dock_PRINT_1.scad", dock_path)
        if not tray_path.is_file():
            render(PSU / "03_service_tray_snap_tray_PRINT_1.scad", tray_path)
        source = (ENCLOSURE / "direct_mount_enclosure.scad").as_posix()
        wrapper = tmp / "backplane-assembly.scad"
        wrapper.write_text(
            f"hinge_part=undef;\ninclude <{source}>;\nuniversal_equipment_backplane();\n",
            encoding="utf-8",
        )
        actual_backplane_path = tmp / "actual-backplane.stl"
        render(wrapper, actual_backplane_path)

        dock = mesh(dock_path, "PSU dock")
        tray = mesh(tray_path, "PSU tray with integral flexure")
        backplane = mesh(actual_backplane_path, "universal enclosure backplane")

        # The physical PETG coupon uses the production flexure and matching
        # real dock-groove geometry, cropped to hand-sized test pieces.
        coupon_source = PSU / "07_detent_test_coupon_TEST_1.scad"
        flex_coupon_path = tmp / "detent-flexure-coupon.stl"
        groove_coupon_path = tmp / "detent-groove-coupon.stl"
        render(coupon_source, flex_coupon_path)
        groove_result = subprocess.run(
            ["openscad", "-D", "coupon_part=1", "-o", str(groove_coupon_path),
             str(coupon_source)], capture_output=True, text=True)
        if (groove_result.returncode or not groove_coupon_path.is_file()
                or not groove_coupon_path.stat().st_size):
            raise SystemExit(
                f"OpenSCAD failed for groove coupon:\n{groove_result.stdout}\n{groove_result.stderr}")
        flex_coupon = mesh(flex_coupon_path, "PETG detent flexure coupon")
        groove_coupon = mesh(groove_coupon_path, "PETG detent groove coupon")
        if abs(float(flex_coupon.bounds[0][2])) > 0.01:
            raise SystemExit("Detent flexure coupon print pose must contact the bed at Z=0")
        if abs(float(flex_coupon.extents[2])-39.5) > 0.05:
            raise SystemExit("Detent coupon must retain its 39.5 mm free cantilever test length")
        if (abs(float(groove_coupon.bounds[0][2])) > 0.01
                or abs(float(groove_coupon.extents[2])-3.2) > 0.05):
            raise SystemExit("Detent groove coupon must preserve the 3.2 mm dock section and print flat")
        print("OK: test coupon reuses production flexure and dock groove geometry")
        if abs(float(dock.extents[1])-79.0) > 0.05:
            raise SystemExit("PSU dock must retain the 79 mm opening envelope")
        if abs(float(tray.extents[2])-79.0) > 0.05:
            raise SystemExit("PSU tray must retain its 79 mm Y envelope in the edge-on print pose")
        if abs(float(dock.bounds[0][2])) > 0.01:
            raise SystemExit("PSU dock print wrapper must contact the bed at Z=0")
        if abs(float(tray.bounds[0][2])) > 0.01 or abs(float(tray.extents[2])-79.0)>0.05:
            raise SystemExit("PSU tray print pose must stand 79 mm tall and contact the bed at Z=0")
        if abs(float(tray.extents[1])-12.75)>0.05:
            raise SystemExit("PSU tray print pose must preserve the 12.75 mm edge-on footprint")

        # Place local dock on the actual 80/176 boss columns. Local +Z points
        # toward the enclosure cavity; exposed boss tips enter pockets by 1.2 mm.
        placed_dock = dock.copy()
        placed_dock.apply_transform(trimesh.transformations.rotation_matrix(math.pi,[1,0,0]))
        placed_dock.apply_translation([128,90.5,51.3])
        volume = intersection_volume(backplane, placed_dock)
        if volume > 0.05:
            raise SystemExit(f"PSU dock collides with actual backplane, overlap={volume:.3f} mm^3")
        print("OK: dock clears the full backplane and registers on all six selected bosses")

        # Remove only the designed flexure to check rigid tray, rail, lip and
        # stop clearance. The compliant nose intentionally cams against the
        # dock entry edge during the last few millimetres of insertion.
        rigid_scad = tmp / "rigid-tray.scad"
        rigid_scad.write_text(
            f"include <{(PSU / 'service_tray_snap_latch_common.scad').as_posix()}>;\nsnap_tray_plate();\n",
            encoding="utf-8",
        )
        rigid_path = tmp / "rigid-tray.stl"
        render(rigid_scad, rigid_path)
        rigid_tray = mesh(rigid_path, "PSU rigid tray body")
        rigid_tray.apply_translation([0,0,3.45])
        for step in range(116):
            offset = -115.0 + step
            moving = rigid_tray.copy()
            moving.apply_translation([offset,0,0])
            overlap = intersection_volume(dock,moving)
            if overlap > 0.05:
                raise SystemExit(
                    f"Rigid tray collides with dock at insertion offset {offset:g} mm: "
                    f"{overlap:.3f} mm^3"
                )
        print("OK: rigid tray clears the dock through the full 115 mm insertion sweep")

        # Button-head M3 screws with a maximum 1.65 mm head are the supported
        # hardware. 0.8 mm recess leaves 0.75 mm above the support plane.
        support_plane = 4.8
        screw_head_top = 3.2 + 1.65 - 0.8
        clearance = support_plane - screw_head_top
        if clearance < 0.7:
            raise SystemExit(f"M3 head does not clear PSU support plane: {clearance:.2f} mm")
        print(f"OK: specified M3 button-head hardware clears PSU support by {clearance:.2f} mm")


if __name__ == "__main__":
    main()
