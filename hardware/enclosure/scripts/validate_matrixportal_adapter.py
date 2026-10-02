#!/usr/bin/env python3
"""Validate issue #178 MatrixPortal adapter mesh and its enclosure context."""
from __future__ import annotations

import argparse
import re
import subprocess
import tempfile
import warnings
from pathlib import Path

import trimesh

ROOT = Path(__file__).resolve().parents[3]
ENCLOSURE = ROOT / "hardware/enclosure"
MATRIXPORTAL = ENCLOSURE / "matrixportal"
PRINT_SOURCE = MATRIXPORTAL / "01_matrixportal_adapter_PRINT_1.scad"
PREVIEW_SOURCE = MATRIXPORTAL / "02_matrixportal_adapter_fit_preview.scad"
OVERLAY_SOURCE = MATRIXPORTAL / "03_matrixportal_hole_overlay_1_TO_1.scad"


def render(source: Path, output: Path, *args: str) -> None:
    result = subprocess.run(["openscad", *args, "-o", str(output), str(source)],
                            capture_output=True, text=True)
    if result.returncode or not output.is_file() or output.stat().st_size == 0:
        raise SystemExit(f"OpenSCAD failed for {source}:\n{result.stdout}\n{result.stderr}")


def intersection_volume(a: trimesh.Trimesh, b: trimesh.Trimesh) -> float:
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=RuntimeWarning)
        result = trimesh.boolean.intersection([a, b], engine="manifold")
    if isinstance(result, list):
        return sum(float(part.volume) for part in result)
    return float(result.volume) if isinstance(result, trimesh.Trimesh) else 0.0


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--generated-dir", type=Path)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="matrixportal-adapter-validation-") as temp:
        tmp = Path(temp)
        generated = args.generated_dir.resolve() if args.generated_dir else tmp
        generated.mkdir(parents=True, exist_ok=True)
        mesh_path = generated / "08_matrixportal_adapter_PRINT_1.stl"
        render(PRINT_SOURCE, mesh_path)
        mesh = trimesh.load(mesh_path, force="mesh", process=True)
        if not isinstance(mesh, trimesh.Trimesh) or mesh.is_empty:
            raise SystemExit("Adapter STL did not load as a non-empty mesh")
        mesh.update_faces(mesh.nondegenerate_faces())
        mesh.remove_unreferenced_vertices()
        components = mesh.split(only_watertight=False)
        if not mesh.is_watertight or len(components) != 1:
            raise SystemExit("Adapter must be one connected watertight solid")
        if mesh.volume <= 0 or abs(float(mesh.bounds[0][2])) > 0.01:
            raise SystemExit("Adapter must have positive volume and bed contact at Z=0")
        expected = [66.0, 60.0, 11.2]
        extents = mesh.extents
        if any(abs(float(extents[i])-expected[i]) > 0.05 for i in range(3)):
            raise SystemExit(f"Unexpected adapter print bounds: {extents.tolist()}")
        print(f"OK: adapter is one watertight component; bounds={mesh.bounds.tolist()}")

        # Compare the installed, boss-registered adapter against the true
        # backplane mesh, then check the board assembly through the whole hinge
        # service arc at the repository's seven canonical angles.
        backplane_scad = tmp / "backplane.scad"
        backplane_scad.write_text(
            f'include <{(ENCLOSURE / "direct_mount_enclosure.scad").as_posix()}>;\n'
            'universal_equipment_backplane();\n', encoding="utf-8")
        backplane_path = tmp / "backplane.stl"
        render(backplane_scad, backplane_path)
        backplane = trimesh.load(backplane_path, force="mesh", process=True)
        installed_scad = tmp / "installed-adapter.scad"
        installed_scad.write_text(
            f'include <{(MATRIXPORTAL / "matrixportal_adapter_common.scad").as_posix()}>;\n'
            'matrixportal_adapter_installed(false);\n', encoding="utf-8")
        installed_path = tmp / "installed-adapter.stl"
        render(installed_scad, installed_path)
        installed = trimesh.load(installed_path, force="mesh", process=True)
        overlap = intersection_volume(backplane, installed)
        if overlap > 0.05:
            raise SystemExit(f"Installed adapter intersects the real backplane by {overlap:.3f} mm^3")
        print("OK: boss pockets register against the real backplane without rigid overlap")

        panel_scad = tmp / "panel-sweep.scad"
        for angle in (0, 15, 30, 45, 60, 75, 90):
            panel_scad.write_text(
                f'include <{(ENCLOSURE / "direct_mount_enclosure.scad").as_posix()}>;\n'
                f'moving_panel_at_angle({angle});\n', encoding="utf-8")
            panel_path = tmp / f"panel-{angle}.stl"
            render(panel_scad, panel_path)
            panel = trimesh.load(panel_path, force="mesh", process=True)
            overlap = intersection_volume(installed, panel)
            if overlap > 0.05:
                raise SystemExit(f"MatrixPortal adapter collides with panel at {angle}°: {overlap:.3f} mm^3")
        print("OK: installed adapter clears the panel at 0°, 15°, 30°, 45°, 60°, 75° and 90°")

        # Ensure the complete in-context assembly and the board-only 1:1 SVG
        # both render. The actual board/connector fit still needs physical QA.
        preview_path = tmp / "matrixportal-fit-preview.stl"
        render(PREVIEW_SOURCE, preview_path)
        print("OK: enclosure, MatrixPortal and PSU context preview renders")
        overlay_path = tmp / "matrixportal-hole-overlay.svg"
        render(OVERLAY_SOURCE, overlay_path)
        svg = overlay_path.read_text(encoding="utf-8")
        root = re.search(r'<svg width="([\d.]+)mm" height="([\d.]+)mm" viewBox="(-?[\d.]+) (-?[\d.]+) ([\d.]+) ([\d.]+)"', svg)
        if not root:
            raise SystemExit("1:1 SVG overlay is missing physical page dimensions")
        page_w, page_h = float(root.group(1)), float(root.group(2))
        view_w, view_h = float(root.group(5)), float(root.group(6))
        source = (MATRIXPORTAL / "matrixportal_adapter_common.scad").read_text()
        if (abs(page_w-view_w) > 0.01 or abs(page_h-view_h) > 0.01
                or "pcb_w = 63.5;" not in source or "pcb_h = 44.45;" not in source):
            raise SystemExit("1:1 SVG scale or 63.5 x 44.45 mm PCB dimensions are incorrect")
        print("OK: 1:1 PCB hole-pattern SVG renders at the specified board size")


if __name__ == "__main__":
    main()
