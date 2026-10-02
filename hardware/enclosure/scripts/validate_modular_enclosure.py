#!/usr/bin/env python3
"""Validate the canonical modular hinged direct-mount enclosure."""

from __future__ import annotations

import argparse
import hashlib
import subprocess
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import partial
from pathlib import Path
from typing import Callable

import numpy as np
import trimesh
from scipy import ndimage

ROOT = Path(__file__).resolve().parents[3]
DIRECT = ROOT / "hardware/enclosure"
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
    "00_complete_enclosure_OPEN_ASSEMBLY.scad",
    "00_complete_enclosure_CLOSED_ASSEMBLY.scad",
)

Check = tuple[str, Callable[[], None]]


def run_parallel_checks(checks: list[Check], workers: int) -> None:
    """Run independent OpenSCAD checks with bounded concurrency."""
    if workers <= 1:
        for name, check in checks:
            started = time.perf_counter()
            check()
            print(f"TIMING: {name} {time.perf_counter() - started:.1f}s", flush=True)
        return

    print(f"Running {len(checks)} independent checks with {workers} workers", flush=True)

    def timed(check: Callable[[], None]) -> float:
        started = time.perf_counter()
        check()
        return time.perf_counter() - started

    failures: list[tuple[str, BaseException]] = []
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(timed, check): name
            for name, check in checks
        }
        for future in as_completed(futures):
            name = futures[future]
            try:
                elapsed = future.result()
                print(f"TIMING: {name} {elapsed:.1f}s", flush=True)
            except (Exception, SystemExit) as exc:
                failures.append((name, exc))

    if failures:
        detail = "\n\n".join(f"{name}: {exc}" for name, exc in failures)
        raise SystemExit(f"parallel enclosure validation failed:\n{detail}")


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

def canonical_stl_hash(path: Path) -> str:
    """Hash STL triangle geometry independent of facet/vertex ordering."""
    triangles: list[tuple[tuple[float, float, float], ...]] = []
    vertices: list[tuple[float, float, float]] = []

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
        raise SystemExit(f"{path}: incomplete STL triangle data")
    if not triangles:
        raise SystemExit(f"{path}: no STL triangles found")

    payload = repr(sorted(triangles)).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def assert_tracked_stl_current(stl_name: str, generated: Path) -> None:
    tracked = DIRECT / "stl" / stl_name
    if not tracked.is_file():
        raise SystemExit(
            f"missing canonical STL: {tracked.relative_to(ROOT)}; "
            "regenerate and commit the STL with its SCAD change"
        )

    if canonical_stl_hash(generated) != canonical_stl_hash(tracked):
        raise SystemExit(
            f"stale canonical STL: {tracked.relative_to(ROOT)}; "
            "regenerate it from the matching SCAD wrapper"
        )

    print(f"OK: {stl_name} matches checked-in canonical STL")


def load_mesh(name: str, path: Path) -> trimesh.Trimesh:
    loaded = trimesh.load_mesh(path, process=True)
    if isinstance(loaded, trimesh.Scene):
        if not loaded.geometry:
            raise SystemExit(f"{name}: mesh scene contains no geometry")
        loaded = trimesh.util.concatenate(tuple(loaded.geometry.values()))
    if not isinstance(loaded, trimesh.Trimesh) or loaded.is_empty:
        raise SystemExit(f"{name}: could not load a non-empty mesh")
    # OpenSCAD 2026 can emit an opposite-wound pair of zero-area triangles at
    # an exactly coplanar connector-pad edge. They have no printable volume;
    # remove only degenerate faces before watertightness/component checks.
    loaded.update_faces(loaded.nondegenerate_faces())
    loaded.remove_unreferenced_vertices()
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
    pitch_mm: float = 2.0,
    support_radius_voxels: int = 1,
    min_component_voxels: int = 2,
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
        component_sizes = np.bincount(labels.ravel(), minlength=count + 1)
        supported_ids = np.unique(labels[supported_xy & current])
        supported_components = np.zeros(count + 1, dtype=bool)
        supported_components[supported_ids] = True
        unsupported_ids = np.flatnonzero(
            (component_sizes >= min_component_voxels) & ~supported_components
        )
        unsupported_ids = unsupported_ids[unsupported_ids != 0]
        for component_id in unsupported_ids[: 5 - len(unsupported)]:
            unsupported.append((z_index, int(component_sizes[component_id])))
        if len(unsupported) >= 5:
            break

    if unsupported:
        detail = ", ".join(
            f"z-index {z} ({size} voxels)" for z, size in unsupported
        )
        raise SystemExit(f"{name}: unsupported elevated slice component(s): {detail}")
    print(f"OK: {name} floating-layer proxy")

def assert_empty_intersection(
    work_dir: Path, name: str, body: str, *, declarations: str = ""
) -> None:
    check_scad = work_dir / f"{name}.scad"
    output = work_dir / f"{name}.stl"
    check_scad.write_text(
        f"include <{SOURCE.as_posix()}>;\n{declarations}\n"
        f"intersection() {{\n{body}\n}}\n",
        encoding="utf-8",
    )
    completed = subprocess.run(
        ["openscad", "-o", str(output), str(check_scad)],
        text=True,
        capture_output=True,
    )
    diagnostic = f"{completed.stdout}\n{completed.stderr}"
    if completed.returncode == 0 and output.is_file():
        # OpenSCAD can export a degenerate STL for exact coplanar contact.
        # Treat only an intersection with measurable extent in all three axes
        # as a real 3D collision. A zero-thickness face is contact, not volume.
        contact = load_mesh(name, output)
        components = contact.split(only_watertight=False)
        volumetric = [component for component in components if min(component.extents) > 0.01]
        if volumetric:
            collision = max(volumetric, key=lambda component: component.volume)
            dims = collision.extents
            raise SystemExit(
                f"{name}: geometry intersection has 3D extent "
                f"{dims.tolist()} mm; bounds={collision.bounds.tolist()}"
            )
        dims = contact.extents
        print(
            f"OK: {name} has contact-only intersection; bounds "
            f"{dims[0]:.3f} x {dims[1]:.3f} x {dims[2]:.3f} mm"
        )
        return
    if (
        completed.returncode != 0
        and "Current top level object is empty" not in diagnostic
    ):
        raise SystemExit(f"{name}: intersection evaluation failed:\n{diagnostic}")
    print(f"OK: {name} has no volumetric interference")

def assert_hinge_sweep(work_dir: Path, workers: int) -> None:
    """Guard the proven PR #119 motion, shelf and 6 mm rod clearance."""
    checks: list[Check] = [
        (
            "hinge_rod_stationary_clearance",
            partial(
                assert_empty_intersection,
                work_dir,
                "hinge_rod_stationary_clearance",
                """    stationary_equipment_enclosure();
    hinge_rail_preview();""",
            ),
        ),
    ]
    for angle in (0, 15, 30, 45, 60, 75, 90):
        body = f"""    stationary_equipment_enclosure();

    translate([0,hinge_axis_y,hinge_axis_z])
        rotate([-{angle},0,0])
            translate([0,-hinge_axis_y,-hinge_axis_z])
                moving_panel_template_installed();"""
        floor_check = f"""    intersection() {{
        translate([-1,-100,-1]) cube([module_w+2,100,hinge_axis_z+hinge_radius+2]);
        translate([0,hinge_axis_y,hinge_axis_z])
            rotate([-{angle},0,0])
                translate([0,-hinge_axis_y,-hinge_axis_z])
                    moving_panel_template_installed();
    }}"""
        panel_rod = f"""    translate([0,hinge_axis_y,hinge_axis_z])
        rotate([-{angle},0,0])
            translate([0,-hinge_axis_y,-hinge_axis_z])
                moving_panel_template_installed();
    hinge_rail_preview();"""
        checks.extend(
            [
                (
                    f"hinge_sweep_{angle}",
                    partial(
                        assert_empty_intersection,
                        work_dir,
                        f"hinge_sweep_{angle}",
                        body,
                    ),
                ),
                (
                    f"hinge_floor_clearance_{angle}",
                    partial(
                        assert_empty_intersection,
                        work_dir,
                        f"hinge_floor_clearance_{angle}",
                        floor_check,
                    ),
                ),
                (
                    f"hinge_rod_panel_clearance_{angle}",
                    partial(
                        assert_empty_intersection,
                        work_dir,
                        f"hinge_rod_panel_clearance_{angle}",
                        panel_rod,
                    ),
                ),
            ]
        )
    run_parallel_checks(checks, workers)


def assert_design_contract(work_dir: Path) -> None:
    """Check the reinforced hinge and tapered top-down backplane contract."""
    check_scad = work_dir / "design_contract.scad"
    output = work_dir / "design_contract.csg"
    check_scad.write_text(
        f"""include <{SOURCE.as_posix()}>;
assert(abs(hinge_install_lift-20) < 0.01 &&
       abs(baseline_ground_clearance-20) < 0.01 &&
       abs(ground_clearance-40) < 0.01,
       "installed hinge/panel lift must remain 20 mm above the 20 mm baseline");
assert(abs(hinge_axis_y-ground_clearance) < 0.01,
       "hinge axis must be centred on the moving panel lower edge");
assert(abs(hinge_rail_start_x-10) < 0.01 &&
       abs(hinge_rail_length-236) < 0.01 &&
       abs(hinge_rail_end_x-246) < 0.01,
       "hinge rail endpoints must remain X=10..246 mm");
assert(side_rod_sleeve_outer_d >= hinge_outer_d-0.01 &&
       side_rod_sleeve_bore_d >= hinge_rail_d+0.8,
       "side rod sleeve must be hinge-sized outside with clearance around the 6 mm rail");
assert((side_rod_sleeve_outer_d-side_rod_sleeve_bore_d)/2 >= 2.5,
       "side rod sleeve wall is too thin");
assert(abs(left_side_inner_x+left_rail_end_stop_len-hinge_rail_start_x) < 0.01,
       "left capped rod stop no longer reaches the left rail endpoint");
assert(abs(right_side_inner_x-right_rail_end_stop_len-hinge_rail_end_x) < 0.01,
       "right capped rod stop no longer reaches the right rail endpoint");
assert(abs(left_side_inner_x+left_side_rod_support_len-hinge_left_barrel_start) < 0.01,
       "left rod support no longer reaches the nearest hinge barrel");
assert(abs(right_side_inner_x-right_side_rod_support_len-hinge_right_barrel_end) < 0.01,
       "right rod support no longer reaches the nearest hinge barrel");
assert(abs(left_side_rod_sleeve_len-
           (hinge_left_barrel_start-hinge_rail_start_x)) < 0.01,
       "left hollow sleeve no longer covers the rod-to-barrel span");
assert(abs(right_side_rod_sleeve_len-
           (hinge_rail_end_x-hinge_right_barrel_end)) < 0.01,
       "right hollow sleeve no longer covers the rod-to-barrel span");
assert(hinge_axis_y-hinge_radius < ground_clearance &&
       hinge_axis_y+hinge_radius > ground_clearance,
       "hinge barrel must straddle the moving panel lower edge");
assert(abs(base_front_extension-20) < 0.01 &&
       abs(base_floor_front_z-(service_front_z-base_front_extension)) < 0.01,
       "stationary base floor must extend 20 mm toward the front");
assert(abs(base_panel_clearance_y-
           min(base_seat_y,ground_clearance-hinge_axis_z)) < 0.01 &&
       base_panel_clearance_z > hinge_axis_z+moving_plate_t,
       "base front relief threshold must follow the raised open-panel clearance");
assert(base_panel_clearance_y >= base_seat_y-0.01,
       "raised hinge should leave the extended structural floor unrelieved");
assert(hinge_guard_t >= 2, "hinge shelf is too thin");
assert(hinge_guard_start_y <= base_seat_y && hinge_guard_top_y >= hinge_axis_y,
       "hinge shelf no longer spans behind the hinge");
assert(hinge_guard_front_z >= hinge_axis_z + hinge_radius + hinge_guard_clearance,
       "hinge shelf violates barrel clearance");
assert(hinge_support_root_t >= 3, "hinge root reinforcement is too thin");
assert(hinge_support_landing_y >= hinge_guard_start_y &&
       hinge_support_landing_y+3 <= hinge_guard_top_y,
       "hinge root web no longer lands within the horizontal shelf");
assert(hinge_support_landing_z < hinge_guard_front_z+hinge_guard_t &&
       hinge_support_landing_z+hinge_support_landing_h > hinge_guard_front_z+hinge_guard_t,
       "hinge root web must overlap the shelf by design");
assert(abs(hinge_support_base_y-service_base_y) < 0.01 &&
       hinge_support_base_h > 0 &&
       hinge_support_base_y+hinge_support_base_h <= base_panel_clearance_y+0.01,
       "hinge support must land inside the retained structural base floor");
assert(hinge_support_base_z >= base_floor_front_z &&
       hinge_support_base_z+hinge_support_base_t <= base_floor_rear_z,
       "hinge support base anchor must remain embedded in the base floor");

assert(abs(enclosure_bottom_depth-40) < 0.01,
       "lower equipment depth must remain 40 mm");
assert(abs(backplane_ramp_start_y-75) < 0.01,
       "backplane taper must start 75 mm above the floor");
assert(abs(backplane_ramp_end_y-120) < 0.01,
       "backplane taper must reach shallow depth at 120 mm");
assert(abs(enclosure_top_y-(ground_clearance+module_h)) < 0.01,
       "stationary enclosure must match the lifted full front-panel height");
assert(abs(upper_vertical_h-(28+hinge_install_lift)) < 0.01,
       "native shallow upper wall must absorb the 20 mm panel lift");

assert(abs(universal_deep_clear_depth-54) < 0.01,
       "universal deep cavity must retain 54 mm clear depth");
assert(abs(universal_deep_x0-service_x) < 0.01 &&
       abs(universal_deep_x1-(service_x+service_w)) < 0.01 &&
       abs(universal_deep_w-service_w) < 0.01,
       "universal shell must keep one full-width profile across X");
assert(abs(universal_full_x0-universal_deep_x0) < 0.01 &&
       abs(universal_full_x1-universal_deep_x1) < 0.01 &&
       abs(universal_full_w-universal_deep_w) < 0.01,
       "full-width aliases must match the constant universal profile");
assert(abs(universal_deep_y0-side_guide_y1) < 0.01,
       "full-depth shell must begin immediately above the guide/insertion section");
assert(abs(universal_psu_h-80) < 0.01 &&
       abs(universal_psu_vertical_clearance-4) < 0.01,
       "measured PSU height/clearance contract drifted");
assert(abs(universal_deep_y1-
           (universal_deep_y0+universal_guide_shoulder_t+
            universal_psu_h+universal_psu_vertical_clearance)) < 0.01,
       "deep rear wall must preserve PSU height ABOVE the reinforced shoulder");
assert(abs(universal_deep_y1-
           (universal_deep_y0+universal_guide_shoulder_t)-84) < 0.01,
       "usable full-depth height above the shoulder must remain 84 mm");
assert(abs(universal_return_ramp_h-12) < 0.01 &&
       abs(universal_deep_ramp_end_y-universal_deep_y1-
           universal_return_ramp_h) < 0.01,
       "upper return ramp must retain the 12 mm ventilated profile");
assert(abs(universal_top_flat_h-23.5) < 0.01 &&
       abs(universal_deep_ramp_end_y-
           (enclosure_top_y-universal_top_flat_h)) < 0.01,
       "raised enclosure must leave a 23.5 mm shallow closure wall");
assert(abs(universal_deep_ramp_end_y-144.5) < 0.01,
       "restored ventilated return-ramp endpoint drifted");
assert(universal_deep_front_z-enclosure_front_z >= 54-0.01,
       "universal deep cavity lost required equipment depth");
assert(universal_deep_w >= 110+6,
       "flat universal area is too narrow for the 110 mm PSU plus clearance");
assert(universal_deep_y1-
           (universal_deep_y0+universal_guide_shoulder_t) >= 80+4,
       "usable cavity above the reinforced shoulder is too short for the 80 mm PSU plus clearance");
assert(universal_deep_clear_depth >= 37+10,
       "universal cavity is too shallow for the 37 mm PSU plus service clearance");
assert(universal_deep_clear_depth-adapter_boss_h >= 37+10,
       "PSU loses too much depth where the inward boss rows overlap its footprint");
assert(len(adapter_y) == 3,
       "universal accessory grid must use exactly three boss rows");
assert(abs(adapter_edge_inset_y-27) < 0.01,
       "outer boss-row edge inset must remain 27 mm after physical-fit correction");
assert(abs(adapter_y[0]-(universal_deep_y0+adapter_edge_inset_y)) < 0.01 &&
       abs(adapter_y[1]-(universal_deep_y0+universal_deep_y1)/2) < 0.01 &&
       abs(adapter_y[2]-(universal_deep_y1-adapter_edge_inset_y)) < 0.01,
       "boss rows must remain centred with symmetric outer rows");
assert(adapter_y[0] > universal_deep_y0 &&
       adapter_y[2] < universal_deep_y1 &&
       adapter_y[0] < adapter_y[1] &&
       adapter_y[1] < adapter_y[2],
       "boss rows must remain ordered inside the full-depth universal wall");
assert(abs(adapter_boss_d-7) < 0.01 &&
       abs(adapter_boss_h-4) < 0.01,
       "accessory bosses must retain the slimmer 7 mm OD x 4 mm height");

// Ventilation belongs on the lower shoulder and restored 12 mm upper return
// ramp. The raised hinge provides enough upper height to keep the complete
// 84 mm usable PSU envelope while returning the top vents to the ramp.
assert(abs(vent_slot_len-24) < 0.01 &&
       abs(vent_slot_gap-10) < 0.01 &&
       vent_slot_count == 7,
       "ramp vent slot layout drifted");
assert(abs(vent_slot_y_h-1.0) < 0.01,
       "ramp vent throat drifted");
assert(universal_return_ramp_h >= 4,
       "upper return ramp became shorter than the proven side-on profile");
assert(universal_guide_shoulder_t >= 8,
       "lower tongue/deep-shell transition shoulder is too thin");
assert(len(transition_rib_centres) == 3 &&
       abs(transition_rib_centres[0]-64) < 0.01 &&
       abs(transition_rib_centres[1]-128) < 0.01 &&
       abs(transition_rib_centres[2]-192) < 0.01,
       "transition reinforcement must retain three distributed rear ribs");
assert(abs(transition_rib_half_w-12) < 0.01 &&
       abs(transition_rib_slice_w-1.0) < 0.01,
       "transition rear-rib taper width drifted");
assert(abs(rear_reinforcement_flush_z-
           (side_guide_rear_z+side_guide_rear_buttress_depth)) < 0.01,
       "rear guide buttresses and rib projections must share one flush rear plane");
assert(abs(transition_rib_depth-
           (rear_reinforcement_flush_z-equipment_backplane_rear_z)) < 0.01,
       "transition ribs must reach the common rear reinforcement plane");
assert(abs(transition_rib_y0-
           (base_seat_y+side_guide_clearance)) < 0.01 &&
       abs(transition_rib_y1-
           (universal_deep_y0+universal_guide_shoulder_t)) < 0.01,
       "transition ribs must stop 0.6 mm above the base seat and bridge into the reinforced shoulder");
assert(abs(rear_guardrail_y0-service_base_y) < 0.01 &&
       abs(rear_guardrail_y1-
           (base_seat_y+side_guide_clearance)) < 0.01 &&
       rear_guardrail_y1-rear_guardrail_y0 >= 4.5,
       "rear guardrail tabs must rise to the rib lower edge without entering the 2 mm seat");
assert(abs(rear_guardrail_lip_front_z-side_guide_slot_back_z) < 0.01 &&
       abs(rear_guardrail_lip_rear_z-side_guide_rear_z) < 0.01,
       "rear guardrail tabs must continue the side-guide rear lip");
assert(abs(rear_guardrail_tab_w-
           (transition_rib_channel_flat_w-2*side_guide_clearance)) < 0.01 &&
       abs(rear_guardrail_join_overlap-0.4) < 0.01,
       "rear guardrail tab width/join overlap drifted");
assert(abs(rear_guardrail_left_x0-service_x) < 0.01 &&
       abs(rear_guardrail_left_x1-
           (transition_rib_centres[0]-rear_guardrail_tab_w/2+
            rear_guardrail_join_overlap)) < 0.01 &&
       rear_guardrail_left_x1-rear_guardrail_left_x0 >= 58,
       "left outer guardrail must run from the side guide to the first rib");
assert(abs(rear_guardrail_right_x1-(service_x+service_w)) < 0.01 &&
       abs(rear_guardrail_right_x0-
           (transition_rib_centres[2]+rear_guardrail_tab_w/2-
            rear_guardrail_join_overlap)) < 0.01 &&
       rear_guardrail_right_x1-rear_guardrail_right_x0 >= 58,
       "right outer guardrail must run from the side guide to the first rib");
assert(rear_guardrail_left_x1 <
           transition_rib_centres[1]-rear_guardrail_tab_w/2 &&
       rear_guardrail_right_x0 >
           transition_rib_centres[1]+rear_guardrail_tab_w/2,
       "outer guardrails must leave the centre span open");
assert(abs(rear_guardrail_shelf_rear_z-rear_reinforcement_flush_z) < 0.01 &&
       rear_guardrail_shelf_top_y <= equipment_backplane_y0-0.19,
       "rear shelf must reach the flush plane while staying below the removable tongue");
assert(abs(transition_rib_channel_w-18) < 0.01 &&
       abs(transition_rib_channel_flat_w-12) < 0.01 &&
       abs(transition_rib_channel_taper_w-3) < 0.01,
       "guardrail channel width/taper drifted");
assert(abs(transition_rib_channel_front_z-side_guide_slot_back_z) < 0.01,
       "guardrail channel must begin at the rear side-guide running envelope");
assert(abs(transition_rib_channel_depth-
           (side_guide_wall_t+side_guide_clearance)) < 0.01 &&
       abs(transition_rib_channel_depth-1.8) < 0.01,
       "guardrail channel must fit the 1.2 mm tab with 0.6 mm rear clearance");
assert(abs(transition_rib_channel_front_z-equipment_backplane_rear_z-
           side_guide_clearance) < 0.01,
       "sliding tongue must retain 0.6 mm clearance before the guardrail channel");
assert(abs(transition_rib_channel_rear_z-rear_guardrail_lip_rear_z-
           side_guide_clearance) < 0.01,
       "guardrail tab must retain 0.6 mm clearance to the rear rib wall");
assert(abs(transition_rib_rear_foot_w-transition_rib_channel_flat_w) < 0.01 &&
       abs(transition_rib_rear_foot_y0-equipment_backplane_y0) < 0.01,
       "rear rib foot must use the 12 mm centre and reach the backplane bottom");
assert(abs(transition_rib_rear_foot_front_z-
           transition_rib_channel_rear_z) < 0.01 &&
       abs(transition_rib_rear_foot_front_z-
           rear_guardrail_lip_rear_z-side_guide_clearance) < 0.01,
       "rear rib foot must begin behind the complete guardrail slot/clearance");
assert(transition_rib_rear_foot_y1 >=
           transition_rib_y0+transition_rib_rear_foot_overlap_y-0.01 &&
       transition_rib_rear_foot_overlap_y >= 0.4,
       "rear rib foot must overlap the upper rib vertically");
assert(abs(transition_rib_rear_foot_rear_z-
           min(rear_reinforcement_flush_z,universal_deep_front_z)) < 0.01 &&
       transition_rib_rear_foot_rear_z >
           transition_rib_rear_foot_front_z,
       "rear rib foot must reach the existing rear reinforcement plane");
assert(rear_guardrail_shelf_top_y <=
           transition_rib_rear_foot_y0-0.19,
       "rear rib foot must stay above the stationary rear shelf");
assert(transition_rib_channel_flat_w-
           2*side_guide_clearance >= 10,
       "guardrail tab lost useful width inside the rib channel");
assert(rear_reinforcement_flush_z <= universal_deep_front_z+0.01,
       "rear reinforcement plane must stay clear of the deep equipment wall");
assert(bottom_ramp_vent_rows == 3 && len(bottom_ramp_vent_y) == 3,
       "lower transition shoulder must carry exactly three ventilation rows");
assert(bottom_ramp_vent_margin_y >= 1.25,
       "lower vent rows lost their structural end margin");
assert(bottom_ramp_vent_row_gap >= 1.25,
       "lower vent rows are too close together");
assert(bottom_ramp_vent_y[0] >=
           universal_deep_y0+bottom_ramp_vent_margin_y-0.01 &&
       bottom_ramp_vent_y[2]+vent_slot_y_h <=
           universal_deep_y0+universal_guide_shoulder_t-
               bottom_ramp_vent_margin_y+0.01,
       "bottom vent rows must remain inside the lower shoulder margins");
for (row=[0:1])
    assert(bottom_ramp_vent_y[row+1] -
               (bottom_ramp_vent_y[row]+vent_slot_y_h) >= 1.25,
           "bottom vent rows lost the minimum solid land between openings");
assert(top_ramp_vent_rows == 4 && len(top_ramp_vent_y) == 4,
       "upper return ramp must carry exactly four ventilation rows");
assert(top_ramp_vent_margin_y >= 1.5,
       "upper vent rows lost their structural end margin");
assert(top_ramp_vent_row_gap >= 1.5,
       "upper vent rows are too close together");
assert(top_ramp_vent_y[0] >=
           universal_deep_y1+top_ramp_vent_margin_y-0.01 &&
       top_ramp_vent_y[3]+vent_slot_y_h <=
           universal_deep_ramp_end_y-top_ramp_vent_margin_y+0.01,
       "top vent rows must remain inside the upper return-ramp margins");
for (row=[0:2])
    assert(top_ramp_vent_y[row+1] -
               (top_ramp_vent_y[row]+vent_slot_y_h) >= 1.5,
           "top vent rows lost the minimum solid land between openings");
assert(vent_slot_x0 >= universal_deep_x0+10 &&
       vent_slot_x0 +
         vent_slot_count*vent_slot_len +
         (vent_slot_count-1)*vent_slot_gap <=
           universal_deep_x1-10,
       "ramp vents lost structural side margin");

// Manufacturing orientation: installed X is the print Z axis. The narrowed
// lower insertion tongue begins above the bed by lower_backplane_edge_inset,
// and only that short gap receives a removable support strip.
assert(abs(backplane_print_shift_z+service_x) < 0.01,
       "backplane print transform must place the left service edge on Z=0");
assert(abs(insertion_print_support_t-1.0) < 0.01 &&
       abs(insertion_print_support_overlap-0.4) < 0.01,
       "insertion support thickness/overlap contract drifted");
assert(abs(insertion_print_support_h-
           (lower_backplane_edge_inset+insertion_print_support_overlap)) < 0.01,
       "insertion support must reach from the bed into the narrowed tongue");
assert(abs(insertion_print_support_y-
           (side_guide_y1-equipment_backplane_y0)) < 0.01,
       "insertion support must cover the complete guide-height tongue");
assert(insertion_print_support_h < 3,
       "temporary insertion support must remain a small breakaway feature");
assert(len(panel_closure_x) == 3,
       "top closure must reuse exactly three panel screw positions");
for (i=[0:2])
    assert(abs(panel_closure_x[i]-panel_mount_x[i]) < 0.01,
           "top closure X position no longer matches panel mounting hole");
assert(abs(panel_closure_y-(ground_clearance+panel_mount_y[1])) < 0.01,
       "top closure Y position no longer matches panel top-row holes");
assert(abs(panel_closure_hole_d-panel_mount_hole_d) < 0.01 &&
       abs(panel_closure_hole_d-4.5) < 0.01,
       "top closure hole diameter must remain the measured 4.5 mm clearance");
assert(panel_closure_y > universal_deep_ramp_end_y &&
       panel_closure_y+panel_closure_hole_d/2 < enclosure_top_y,
       "top closure centres must remain in the final flat wall");
assert(panel_closure_y-panel_closure_hole_d/2 >=
           universal_deep_ramp_end_y+1.0,
       "top closure holes must keep at least 1 mm of material above the ramp bend");
for (xx=panel_closure_x)
    assert(xx-panel_closure_hole_d/2 > service_x &&
           xx+panel_closure_hole_d/2 < service_x+service_w,
           "top closure hole lost backplane edge margin");
assert(top_connector_slot_bottom_y <
           top_connector_y-connector_socket_d/2 &&
       top_connector_slot_top_y >
           top_connector_y+connector_socket_d/2,
       "top connector guide slot must release vertically in both directions");
assert(top_connector_slot_bottom_y + 15 <=
           top_connector_y-top_connector_tab_h/2,
       "top connector guide slot lacks 15 mm downward release travel");
assert(top_connector_pad_y0 <=
           top_connector_y-top_connector_tab_h/2-top_connector_pad_y_margin+0.01 &&
       top_connector_pad_y1 >=
           top_connector_y+top_connector_tab_h/2,
       "compact top connector boss does not surround the seated tab");
assert(top_connector_pad_y1 <= backplane_ramp_start_y+0.01 &&
       top_connector_pad_y1-top_connector_pad_y0 <= 12,
       "compact top connector boss grew back into a long vertical arm");
assert(top_connector_pad_depth >=
           connector_socket_d+2*top_connector_support_margin,
       "compact top connector boss is too shallow for the locating slot");
assert(abs(top_connector_pad_inner_depth-equipment_backplane_t) < 0.01,
       "connector boss must taper back to native rear-wall thickness");
assert(top_connector_pad_seam_w >= connector_socket_depth+0.8 &&
       top_connector_pad_seam_w < top_connector_pad_w,
       "connector boss full-depth seam land must continue beyond the release slot");
assert(top_connector_pad_w-top_connector_pad_seam_w >=
           top_connector_pad_depth-top_connector_pad_inner_depth &&
       top_connector_pad_slice_w <= 1.0+0.01,
       "connector boss X taper is too abrupt for side-on vertical printing");
assert(top_connector_tab_t < connector_socket_d &&
       connector_socket_d-top_connector_tab_t >= 0.8,
       "ramped top connector tab lacks guide-slot clearance");
assert(top_connector_tab_h >=
           2*(top_connector_tab_len-top_connector_tab_root_len),
       "ramped top connector tab is too steep for support-free printing");
assert(top_connector_tab_root_len > top_connector_overlap,
       "ramped top connector tab root does not overlap its support boss");
assert(top_connector_z-connector_socket_d/2 >=
           universal_deep_rear_z-top_connector_pad_depth
               + top_connector_support_margin,
       "top connector is too close to the cavity face of its compact boss");
assert(top_connector_z+connector_socket_d/2 <=
           universal_deep_rear_z-top_connector_support_margin,
       "top connector breaks through the external rear face");
assert(top_connector_y < backplane_ramp_start_y,
       "top connector must remain below the enclosure ramp");
assert(top_connector_y + top_connector_tab_h/2 <=
           backplane_ramp_start_y + 0.01,
       "solid top connector geometry must remain below the enclosure ramp");
assert(top_connector_slot_top_y >=
           backplane_ramp_start_y + top_connector_release_travel,
       "right-end guide slot lacks required upward release travel");
assert(top_connector_slot_top_y < backplane_ramp_end_y,
       "release slot must finish within the ramp below the clamp-support wall");
assert(top_connector_tab_len-top_module_seam_gap >=
           top_connector_min_engagement,
       "top connector has insufficient engagement between adjacent modules");
assert(top_connector_tab_len-top_side_seam_gap >=
           top_connector_min_engagement,
       "top connector has insufficient engagement into the end plates");

assert(abs(backplane_guide_clearance-0.6) < 0.01,
       "rear groove clearance is outside the physical-print fit target");
assert(abs(side_guide_h-40) < 0.01,
       "side guide height must remain 40 mm");
assert(abs(side_guide_w-5) < 0.01,
       "side guide engagement depth must remain 5 mm");
assert(abs(side_guide_clearance-0.6) < 0.01,
       "side-guide running clearance is outside the physical-print fit target");
assert(abs(side_guide_wall_t-backplane_guide_t) < 0.01,
       "side-guide wall thickness must track the base rail wall");
assert(abs(side_guide_front_tie_z0-hinge_guard_front_z) < 0.01 &&
       abs(side_guide_front_tie_h-junction_pad_h) < 0.01,
       "guide front reinforcement must tie the 16 mm junction support into the hinge plate");
assert(junction_pad_front_z > side_guide_front_tie_z0 &&
       side_guide_front_tie_z0 <= hinge_guard_front_z+0.01,
       "guide front tie does not span continuously toward the hinge plate");
assert(abs(side_guide_rear_buttress_depth-10) < 0.01 &&
       abs(side_guide_rear_buttress_slice_h-1.0) < 0.01 &&
       side_guide_rear_buttress_overlap >= 0.3,
       "guide rear buttress must retain the 10 mm triangular base reinforcement");
assert(side_guide_y1 < backplane_ramp_start_y,
       "side guides must end below the enclosure taper");
assert(side_guide_slot_front_z < equipment_backplane_front_z &&
       side_guide_slot_back_z > equipment_backplane_rear_z,
       "U-channel slot does not clear the backplane thickness");
assert(side_guide_front_z < side_guide_slot_front_z &&
       side_guide_rear_z > side_guide_slot_back_z,
       "U-channel lips no longer surround the backplane slot");
assert(abs(lower_backplane_edge_inset-
           (side_guide_wall_t+side_guide_clearance)) < 0.01,
       "lower backplane edge no longer tracks the U-channel outer spine");
assert(lower_backplane_edge_inset < side_guide_w,
       "lower backplane no longer projects into the side channels");
assert(base_connector_y_a - connector_socket_d/2 >=
           side_guide_y0 + connector_edge_margin,
       "A junction is too close to the lower support-pad edge");
assert(base_connector_y_b + connector_socket_d/2 <=
           side_guide_y0 + junction_pad_h - connector_edge_margin,
       "B junction is too close to the upper support-pad edge");
assert(base_connector_y_b-base_connector_y_a >=
           connector_socket_d + connector_edge_margin/2,
       "A/B junctions do not have enough material between them");
assert(abs(base_connector_z_a-base_connector_z_b) < 0.01 &&
       base_connector_z_a > junction_pad_front_z &&
       base_connector_z_a < side_guide_slot_front_z,
       "hidden junction pair must remain ahead of the backplane slot");
assert(base_connector_y_b-base_connector_y_a >
           (connector_pin_d+connector_socket_d)/2,
       "A/B hidden junctions overlap after the vertical offset");
assert(adapter_outer_skin >= 1.0,
       "outside rear skin over blind accessory holes is too thin");
assert(adapter_hole_depth <=
       adapter_boss_h + equipment_backplane_t - adapter_outer_skin + 0.01,
       "accessory hole breaks through the solid outside rear skin");
assert(backplane_seat_depth >= 2.0,
       "rear groove seat is too shallow");
assert(abs(equipment_backplane_y0-(base_seat_y-backplane_seat_depth)) < 0.01,
       "backplane lower edge must seat inside the base groove");
assert(backplane_slot_front_z < equipment_backplane_front_z &&
       backplane_slot_back_z > equipment_backplane_rear_z,
       "rear groove does not clear the backplane thickness");
assert(base_rear_z-backplane_slot_back_z <= backplane_guide_t+0.01,
       "rear locating groove has drifted away from the back edge");
assert(equipment_backplane_front_z-enclosure_front_z >= 35,
       "lower equipment cavity lost too much usable depth");

assert(max(adapter_y) < universal_deep_y1,
       "accessory bosses must remain on the full-depth universal wall");
cube([1,1,1]);
""",
        encoding="utf-8",
    )
    completed = subprocess.run(
        ["openscad", "-o", str(output), str(check_scad)],
        text=True,
        capture_output=True,
    )
    if completed.returncode != 0 or not output.is_file():
        raise SystemExit(
            f"design contract failed:\n{completed.stdout}\n{completed.stderr}"
        )
    print(
        "OK: reinforced hinge, rear top-down groove, dual 40x5 mm U-channels, "
        "lower hidden junctions, front-tied guide roots with 10 mm rear triangular buttresses, "
        "compact upper backplane/end-plate seam bosses, "
        "unchanged moving-panel hinge roots and 20 mm forward base-floor extension, "
        "40 mm installed hinge with 20 mm forward base-floor extension, "
        "54 mm universal deep cavity with 84 mm usable PSU height above the shoulder, "
        "reinforced transition with three tapered rear ribs and guardrail channels, lower-shoulder plus upper-ramp ventilation, "
        "23.5 mm shallow upper closure wall, three central boss rows, "
        "three aligned closure holes and hinge-rail side-sleeve contract"
    )


def assert_neighboring_module_clearance(work_dir: Path, workers: int) -> None:
    """Check a joined two-module row at closed and fully-open positions."""
    checks: list[Check] = []
    for angle in (0, 90):
        declaration = f"""module row_member() {{
    stationary_equipment_module_core();
    hinge_rail_preview();
    translate([0,hinge_axis_y,hinge_axis_z])
        rotate([-{angle},0,0])
            translate([0,-hinge_axis_y,-hinge_axis_z])
                moving_panel_template_installed();
}}
"""
        checks.append(
            (
                f"neighboring_module_clearance_{angle}",
                partial(
                    assert_empty_intersection,
                    work_dir,
                    f"neighboring_module_clearance_{angle}",
                    "row_member();\ntranslate([module_w,0,0]) row_member();",
                    declarations=declaration,
                ),
            )
        )
    run_parallel_checks(checks, workers)


def assert_no_legacy_layout() -> None:
    for path in (DIRECT / "hinge-prototype-v2", DIRECT / "hinge-version"):
        # Ignore Finder metadata-only folders; they are not live SCAD designs
        # and can otherwise make local validation fail after browsing the tree.
        legacy_sources = list(path.rglob("*.scad")) if path.is_dir() else []
        if legacy_sources:
            raise SystemExit(
                f"legacy enclosure SCAD source still exists: {legacy_sources[0]}"
            )

    # Rear cable/ribbon slots remain retired; cabling routes through open
    # module sides. The production wrapper must use the side-on vertical
    # orientation and only the small insertion-tongue breakaway support.
    source_text = SOURCE.read_text(encoding="utf-8")
    for forbidden in ("cable_slot_x", "cable_slot_len", "cable_slot_w", "cable_slot_y"):
        if forbidden in source_text:
            raise SystemExit(
                f"retired rear cable-slot geometry returned: {forbidden}"
            )

    for forbidden in (
        "backplane_print_stabiliser_x",
        "backplane_print_stabiliser(",
        "backplane_print_breakaway_t",
        "ramp_print_support_x",
        "ramp_print_support_levels",
        "ramp_print_support_post(",
        "ramp_print_supports()",
        "universal_edge_transition_y0",
        "universal_edge_transition_y1",
        "universal_edge_rear_shell(",
        "top_connector_pad_ramp_end_y",
        "top_connector_pad_lower_depth",
        "tapered_backplane_rear_z_at_y",
    ):
        if forbidden in source_text:
            raise SystemExit(
                f"retired horizontal-print support/edge-transition geometry returned: {forbidden}"
            )

    for forbidden in (
        "rear_guardrail_shelf();",
        "rear_rib_seat_clearance_cutters();",
        "rear_support_foot_x",
        "rear_support_foot_rear_extension",
        "rear_support_feet()",
    ):
        if forbidden in source_text:
            raise SystemExit(
                f"retired permanent rear-wall foot geometry returned: {forbidden}"
            )

    for required in (
        "ramp_ventilation_cutters()",
        "horizontal_rounded_vent_cutter(",
        "backplane_print_shift_z",
        "insertion_print_support_t",
        "insertion_print_support_overlap",
        "insertion_tongue_print_support()",
        "transition_rear_ribs()",
        "rotate([0,-90,0])",
    ):
        if required not in source_text:
            raise SystemExit(
                f"required side-on vertical print geometry missing: {required}"
            )

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--generated-dir",
        type=Path,
        help="Reuse STL files already generated by CI instead of rendering them again.",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=1,
        help="Maximum number of independent OpenSCAD checks to run concurrently.",
    )
    args = parser.parse_args()
    if args.workers < 1:
        parser.error("--workers must be at least 1")

    generated_dir = args.generated_dir.resolve() if args.generated_dir else None
    assert_no_legacy_layout()
    with tempfile.TemporaryDirectory(prefix="led-hinged-enclosure-") as tmp:
        work_dir = Path(tmp)
        for scad_name, stl_name in PARTS.items():
            source = PARTS_DIR / scad_name
            if generated_dir is None:
                generated = work_dir / stl_name
                render(source, generated)
            else:
                generated = generated_dir / stl_name
                if not generated.is_file():
                    raise SystemExit(f"missing pre-generated STL: {generated}")

            name = source.stem
            assert_mesh_health(name, generated)
            assert_no_floating_layer_islands(name, generated)
            assert_tracked_stl_current(stl_name, generated)

        assert_design_contract(work_dir)
        # The upper ventilation rows deliberately occupy a dedicated band on
        # the rear wall. Keep that band clear of every accessory-boss row
        # rather than incorrectly requiring the entire rear wall to be solid.
        assert_empty_intersection(
            work_dir,
            "vent_adapter_boss_grid_keepout",
            """    ramp_ventilation_cutters();
    for (yy=adapter_y)
        translate([
            universal_deep_x0-1,
            yy-adapter_boss_d/2-2,
            universal_deep_front_z-1
        ])
            cube([
                universal_deep_w+2,
                adapter_boss_d+4,
                universal_deep_wall_t+2
            ]);""",
        )
        assert_empty_intersection(
            work_dir,
            "vent_final_top_wall_keepout",
            """    ramp_ventilation_cutters();
    translate([
        universal_deep_x0-1,
        universal_deep_ramp_end_y,
        -10
    ])
        cube([
            universal_deep_w+2,
            enclosure_top_y-universal_deep_ramp_end_y,
            100
        ]);""",
        )
        assert_empty_intersection(
            work_dir,
            "vent_lower_guide_keepout",
            """    ramp_ventilation_cutters();
    translate([
        universal_deep_x0-1,
        equipment_backplane_y0,
        -10
    ])
        cube([
            universal_deep_w+2,
            universal_deep_y0-equipment_backplane_y0,
            100
        ]);""",
        )
        assert_empty_intersection(
            work_dir,
            "panel_top_closure_holes_clear",
            """    universal_equipment_backplane();
    panel_closure_hole_cutters();""",
        )
        assert_empty_intersection(
            work_dir,
            "backplane_seat_contact",
            """    hinged_equipment_base();
    universal_equipment_backplane();""",
        )
        backplane_checks: list[Check] = []
        for lift in (1, 20, 80, 140):
            backplane_checks.append(
                (
                    f"backplane_top_down_insertion_{lift}",
                    partial(
                        assert_empty_intersection,
                        work_dir,
                        f"backplane_top_down_insertion_{lift}",
                        f"""    hinged_equipment_base();
    translate([0,{lift},0]) universal_equipment_backplane();""",
                    ),
                )
            )
        run_parallel_checks(backplane_checks, args.workers)

        # Prove the side guides are real U-channels rather than solid towers:
        # the slot volume under each 5 mm lip must remain empty through the
        # middle of the 50 mm guide height.
        assert_empty_intersection(
            work_dir,
            "left_side_guide_channel_void",
            """    hinged_equipment_base();
    translate([
        service_x+lower_backplane_edge_inset,
        side_guide_y0+10,
        side_guide_slot_front_z
    ])
        cube([
            side_guide_w-lower_backplane_edge_inset,
            side_guide_h-20,
            side_guide_slot_back_z-side_guide_slot_front_z
        ]);""",
        )
        assert_empty_intersection(
            work_dir,
            "right_side_guide_channel_void",
            """    hinged_equipment_base();
    translate([
        service_x+service_w-side_guide_w,
        side_guide_y0+10,
        side_guide_slot_front_z
    ])
        cube([
            side_guide_w-lower_backplane_edge_inset,
            side_guide_h-20,
            side_guide_slot_back_z-side_guide_slot_front_z
        ]);""",
        )

        # Guard the equipment cavity against a rail/lip creeping back into the
        # usable volume ABOVE the hinge mechanism. The hinge/panel was raised
        # by 20 mm, so the former fixed Y=36 keep-out now legitimately crosses
        # the raised hinge guard/supports. Start dynamically above the barrel
        # envelope instead; the enlarged base and guide reinforcements below
        # that line are intentional structure.
        assert_empty_intersection(
            work_dir,
            "lower_equipment_volume_clear",
            """    hinged_equipment_base();
    translate([
        service_x+5,
        hinge_axis_y+hinge_radius+2,
        enclosure_front_z+5
    ])
        cube([
            service_w-10,
            backplane_ramp_start_y-(hinge_axis_y+hinge_radius+4),
            equipment_backplane_front_z-enclosure_front_z-10
        ]);""",
        )
        # Above the guide section the shell profile is deliberately identical
        # across the complete X length; the parameter contract above guards
        # against reintroducing edge-specific depth transitions.

        # The upper connector aligns modules/end plates without making the
        # removable backplane horizontally captive. Test relative vertical
        # travel through the guide slot in both neighbour and end-plate cases.
        connector_checks: list[Check] = []
        for lift in (1, 5, 10, 15):
            connector_checks.extend(
                [
                    (
                        f"top_connector_neighbor_vertical_release_{lift}",
                        partial(
                            assert_empty_intersection,
                            work_dir,
                            f"top_connector_neighbor_vertical_release_{lift}",
                            f"""    universal_equipment_backplane();
    translate([module_w,{lift},0]) universal_equipment_backplane();""",
                        ),
                    ),
                    (
                        f"top_connector_left_end_vertical_release_{lift}",
                        partial(
                            assert_empty_intersection,
                            work_dir,
                            f"top_connector_left_end_vertical_release_{lift}",
                            f"""    equipment_side("left");
    translate([0,{lift},0]) universal_equipment_backplane();""",
                        ),
                    ),
                    (
                        f"top_connector_right_end_vertical_release_{lift}",
                        partial(
                            assert_empty_intersection,
                            work_dir,
                            f"top_connector_right_end_vertical_release_{lift}",
                            f"""    equipment_side("right");
    translate([0,{lift},0]) universal_equipment_backplane();""",
                        ),
                    ),
                ]
            )
        run_parallel_checks(connector_checks, args.workers)

        side_checks: list[Check] = []
        for side in ("left", "right"):
            side_checks.extend(
                [
                    (
                        f"{side}_side_retainer_fit",
                        partial(
                            assert_empty_intersection,
                            work_dir,
                            f"{side}_side_retainer_fit",
                            f"""    stationary_equipment_module_core();
    equipment_side(\"{side}\");""",
                        ),
                    ),
                    (
                        f"{side}_side_rod_sleeve_clearance",
                        partial(
                            assert_empty_intersection,
                            work_dir,
                            f"{side}_side_rod_sleeve_clearance",
                            f"""    equipment_side(\"{side}\");
    hinge_rail_preview();""",
                        ),
                    ),
                ]
            )
        run_parallel_checks(side_checks, args.workers)
        assert_hinge_sweep(work_dir, args.workers)
        assert_neighboring_module_clearance(work_dir, args.workers)

        preview_checks: list[Check] = [
            (
                f"preview_{Path(preview).stem}",
                partial(
                    render,
                    SCHEMATICS / preview,
                    work_dir / f"{Path(preview).stem}.csg",
                ),
            )
            for preview in PREVIEWS
        ]
        run_parallel_checks(preview_checks, args.workers)
        for preview in PREVIEWS:
            print(f"OK: {preview}", flush=True)

    print("All canonical hinged enclosure checks passed.")

if __name__ == "__main__":
    main()
