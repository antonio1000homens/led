#!/usr/bin/env python3
"""Validate the canonical modular hinged direct-mount enclosure."""

from __future__ import annotations

import hashlib
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

def assert_hinge_sweep(work_dir: Path) -> None:
    """Guard the proven PR #119 motion, shelf and 6 mm rod clearance."""
    assert_empty_intersection(
        work_dir,
        "hinge_rod_stationary_clearance",
        """    stationary_equipment_enclosure();
    hinge_rail_preview();""",
    )
    for angle in (0, 15, 30, 45, 60, 75, 90):
        body = f"""    stationary_equipment_enclosure();

    translate([0,hinge_axis_y,hinge_axis_z])
        rotate([-{angle},0,0])
            translate([0,-hinge_axis_y,-hinge_axis_z])
                moving_panel_template_installed();"""
        assert_empty_intersection(work_dir, f"hinge_sweep_{angle}", body)
        floor_check = f"""    intersection() {{
        translate([-1,-100,-1]) cube([module_w+2,100,hinge_axis_z+hinge_radius+2]);
        translate([0,hinge_axis_y,hinge_axis_z])
            rotate([-{angle},0,0])
                translate([0,-hinge_axis_y,-hinge_axis_z])
                    moving_panel_template_installed();
    }}"""
        assert_empty_intersection(work_dir, f"hinge_floor_clearance_{angle}", floor_check)
        panel_rod = f"""    translate([0,hinge_axis_y,hinge_axis_z])
        rotate([-{angle},0,0])
            translate([0,-hinge_axis_y,-hinge_axis_z])
                moving_panel_template_installed();
    hinge_rail_preview();"""
        assert_empty_intersection(
            work_dir, f"hinge_rod_panel_clearance_{angle}", panel_rod
        )

def assert_design_contract(work_dir: Path) -> None:
    """Check the reinforced hinge and tapered top-down backplane contract."""
    check_scad = work_dir / "design_contract.scad"
    output = work_dir / "design_contract.csg"
    check_scad.write_text(
        f"""include <{SOURCE.as_posix()}>;
assert(abs(hinge_axis_y-ground_clearance) < 0.01,
       "hinge axis must be centred on the moving panel lower edge");
assert(hinge_axis_y-hinge_radius < ground_clearance &&
       hinge_axis_y+hinge_radius > ground_clearance,
       "hinge barrel must straddle the moving panel lower edge");
assert(abs(base_panel_clearance_y-(ground_clearance-hinge_axis_z)) < 0.01 &&
       base_panel_clearance_z > hinge_axis_z+moving_plate_t,
       "base front relief must clear the open panel lower band");
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

assert(abs(enclosure_bottom_depth-40) < 0.01,
       "lower equipment depth must remain 40 mm");
assert(abs(enclosure_top_depth-10) < 0.01,
       "top enclosure depth must remain 10 mm");
assert(abs(backplane_ramp_start_y-60) < 0.01,
       "backplane taper must start 60 mm above the floor");
assert(abs(enclosure_top_y-(ground_clearance+module_h)) < 0.01,
       "backplane roof must reach the top of the front plate");
assert(abs(top_link_front_z-(fixed_template_t+0.8)) < 0.01,
       "top link no longer closes to the template with 0.8 mm clearance");

assert(abs(backplane_guide_clearance-0.4) < 0.01,
       "rear groove clearance is outside the FDM fit target");
assert(abs(side_guide_h-50) < 0.01,
       "side guide height must remain 50 mm");
assert(abs(side_guide_w-5) < 0.01,
       "side guide engagement depth must remain 5 mm");
assert(abs(side_guide_clearance-0.4) < 0.01,
       "side-guide running clearance is outside the FDM fit target");
assert(abs(side_guide_wall_t-backplane_guide_t) < 0.01,
       "side-guide wall thickness must track the base rail wall");
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
assert(base_connector_y_a <= base_seat_y,
       "A junction must remain bed-connected in the floor band");
assert(base_connector_y_b > base_seat_y &&
       base_connector_y_b + connector_socket_d/2 <
           side_guide_y0 + junction_pad_h,
       "B junction must remain fully supported by the internal front pad");
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

assert(max(adapter_y) < backplane_ramp_start_y,
       "accessory bosses must remain on the vertical lower backplane");
assert(upper_vent_y > backplane_ramp_start_y,
       "ventilation must remain in the tapered upper section");
assert(upper_vent_y+upper_vent_h < enclosure_top_y,
       "upper ventilation exceeds the tapered section");
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
        "OK: reinforced hinge, rear top-down groove, dual 50x5 mm U-channels, "
        "hidden junctions, solid outside skin and 40-to-10 mm tapered backplane contract"
    )


def assert_neighboring_module_clearance(work_dir: Path) -> None:
    """Check a joined two-module row at closed and fully-open positions.

    Side retainers are used at the outside edges of a joined row. The
    detachable retainers on the two internal edges are omitted; their base and
    backplane pin/socket features mate directly across the module seam.
    """
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
        assert_empty_intersection(
            work_dir,
            f"neighboring_module_clearance_{angle}",
            "row_member();\ntranslate([module_w,0,0]) row_member();",
            declarations=declaration,
        )

def assert_no_legacy_layout() -> None:
    for path in (DIRECT / "hinge-prototype-v2", DIRECT / "hinge-version"):
        # Ignore Finder metadata-only folders; they are not live SCAD designs
        # and can otherwise make local validation fail after browsing the tree.
        legacy_sources = list(path.rglob("*.scad")) if path.is_dir() else []
        if legacy_sources:
            raise SystemExit(
                f"legacy enclosure SCAD source still exists: {legacy_sources[0]}"
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
            assert_tracked_stl_current(stl_name, generated)

        assert_design_contract(work_dir)
        assert_empty_intersection(
            work_dir,
            "backplane_seat_contact",
            """    hinged_equipment_base();
    universal_equipment_backplane();""",
        )
        for lift in (1, 20, 80, 140):
            assert_empty_intersection(
                work_dir,
                f"backplane_top_down_insertion_{lift}",
                f"""    hinged_equipment_base();
    translate([0,{lift},0]) universal_equipment_backplane();""",
            )

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
        # lower usable volume. Hinge hardware intentionally occupies the first
        # ~30 mm above the floor, so the keep-out starts above that mechanism.
        assert_empty_intersection(
            work_dir,
            "lower_equipment_volume_clear",
            """    hinged_equipment_base();
    translate([
        service_x+5,
        36,
        enclosure_front_z+5
    ])
        cube([
            service_w-10,
            backplane_ramp_start_y-38,
            equipment_backplane_front_z-enclosure_front_z-10
        ]);""",
        )
        for side in ("left", "right"):
            assert_empty_intersection(
                work_dir,
                f"{side}_side_retainer_fit",
                f"""    stationary_equipment_module_core();
    equipment_side(\"{side}\");""",
            )
        assert_hinge_sweep(work_dir)
        assert_neighboring_module_clearance(work_dir)

        for preview in PREVIEWS:
            render(SCHEMATICS / preview, work_dir / f"{Path(preview).stem}.csg")
            print(f"OK: {preview}")

    print("All canonical hinged enclosure checks passed.")

if __name__ == "__main__":
    main()
