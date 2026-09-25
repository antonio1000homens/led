#!/usr/bin/env python3
"""Regenerate hinge prototype v2 STLs and verify checked-in meshes are current."""

from __future__ import annotations

import hashlib
import subprocess
import tempfile
from pathlib import Path

import numpy as np
import trimesh
from scipy import ndimage


ROOT = Path(__file__).resolve().parents[4]
HINGE_DIR = ROOT / "hardware/enclosure/direct-mount/hinge-prototype-v2"

PARTS = {
    "01_moving_panel_template_HINGE_TEST.scad":
        "01_moving_panel_template_HINGE_TEST.stl",
    "02_middle_stationary_enclosure_HINGE_TEST.scad":
        "02_middle_stationary_enclosure_HINGE_TEST.stl",
    "03_left_controller_end_enclosure_HINGE_TEST.scad":
        "03_left_controller_end_enclosure_HINGE_TEST.stl",
    "04_right_power_end_enclosure_HINGE_TEST.scad":
        "04_right_power_end_enclosure_HINGE_TEST.stl",
}


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


def bounds(path: Path) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
    mins = [float("inf")] * 3
    maxs = [float("-inf")] * 3

    with path.open(encoding="utf-8", errors="strict") as handle:
        for raw in handle:
            line = raw.strip()
            if not line.startswith("vertex "):
                continue
            _, xs, ys, zs = line.split()
            vertex = tuple(float(value) for value in (xs, ys, zs))
            for axis, value in enumerate(vertex):
                mins[axis] = min(mins[axis], value)
                maxs[axis] = max(maxs[axis], value)

    return tuple(mins), tuple(maxs)


def assert_on_bed(name: str, path: Path) -> tuple[float, float, float]:
    mins, maxs = bounds(path)
    dims = tuple(maxs[i] - mins[i] for i in range(3))

    if abs(mins[2]) > 0.05:
        raise SystemExit(f"{name} does not sit on print Z=0: min_z={mins[2]:.3f}")

    return dims


def assert_no_floating_layer_islands(
    name: str,
    path: Path,
    *,
    pitch_mm: float = 1.0,
    support_radius_voxels: int = 2,
    min_component_voxels: int = 4,
) -> None:
    """Reject elevated XY slice islands with no support from the layer below.

    This is deliberately a coarse slicer proxy rather than a promise that a
    particular Bambu profile needs no supports. It targets the failure mode we
    actually saw: a roof/landing whose first printable slice appeared detached
    from the already-printed enclosure.

    A component is considered supported when any voxel in that XY component is
    within support_radius_voxels of occupied material in the preceding Z slice.
    This allows ordinary sloped overhangs and short bridges while rejecting a
    genuinely new floating island.
    """

    loaded = trimesh.load_mesh(path, process=True)
    if isinstance(loaded, trimesh.Scene):
        if not loaded.geometry:
            raise SystemExit(f"{name}: mesh scene contains no geometry")
        loaded = trimesh.util.concatenate(tuple(loaded.geometry.values()))

    if not isinstance(loaded, trimesh.Trimesh) or loaded.is_empty:
        raise SystemExit(f"{name}: could not load a non-empty mesh")

    voxels = loaded.voxelized(pitch_mm).fill()
    matrix = np.asarray(voxels.matrix, dtype=bool)

    if matrix.ndim != 3 or not matrix.any():
        raise SystemExit(f"{name}: voxelization produced no printable volume")

    occupied_layers = np.flatnonzero(matrix.any(axis=(0, 1)))
    if occupied_layers.size == 0:
        raise SystemExit(f"{name}: no occupied Z layers after voxelization")

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
        supported_xy = ndimage.binary_dilation(
            previous,
            structure=support_structure,
        )

        labels, component_count = ndimage.label(
            current,
            structure=component_structure,
        )

        for component_id in range(1, component_count + 1):
            component = labels == component_id
            size = int(component.sum())
            if size < min_component_voxels:
                continue
            if np.any(component & supported_xy):
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
        raise SystemExit(
            f"{name} contains elevated layer component(s) with no support "
            f"from the preceding layer at {pitch_mm:.1f} mm voxel pitch: {detail}. "
            "This is a floating-region proxy; inspect the STL in Bambu Studio."
        )

    print(
        f"OK: {name} has no detached elevated XY slice components "
        f"({pitch_mm:.1f} mm floating-layer proxy)"
    )


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        generated_dir = Path(tmp)

        for scad_name, stl_name in PARTS.items():
            generated = generated_dir / stl_name
            tracked = HINGE_DIR / "stl" / stl_name

            subprocess.run(
                ["openscad", "-o", str(generated), str(HINGE_DIR / scad_name)],
                check=True,
            )

            if not tracked.is_file():
                raise SystemExit(f"missing checked-in STL: {tracked}")

            if canonical_hash(generated) != canonical_hash(tracked):
                raise SystemExit(
                    f"stale hinge v2 STL: {tracked}\n"
                    f"Regenerate it from {HINGE_DIR / scad_name}."
                )

            print(f"OK: {scad_name} -> stl/{stl_name}")

        template = generated_dir / PARTS["01_moving_panel_template_HINGE_TEST.scad"]
        template_dims = assert_on_bed("moving panel template", template)

        if template_dims[2] > 18.0:
            raise SystemExit(
                "moving panel template gained excessive rear/lip geometry: "
                f"height={template_dims[2]:.1f} mm (expected <= 18 mm)"
            )

        enclosure_specs = (
            (
                "middle stationary enclosure",
                "02_middle_stationary_enclosure_HINGE_TEST.scad",
                260.0,
            ),
            (
                "left controller end enclosure",
                "03_left_controller_end_enclosure_HINGE_TEST.scad",
                262.0,
            ),
            (
                "right power end enclosure",
                "04_right_power_end_enclosure_HINGE_TEST.scad",
                262.0,
            ),
        )

        print(
            "OK: moving template print bounds "
            f"{template_dims[0]:.1f} x {template_dims[1]:.1f} x {template_dims[2]:.1f} mm"
        )


        for name, scad_name, max_width in enclosure_specs:
            enclosure = generated_dir / PARTS[scad_name]
            enclosure_dims = assert_on_bed(name, enclosure)

            # All stationary variants print upright on the real floor base:
            # Y ~= 68 mm total front/rear footprint, Z ~= 148 mm.
            # End variants are a few mm wider because their closure wall sits
            # primarily outside the 256 mm LED/template footprint.
            if enclosure_dims[2] > 155.0:
                raise SystemExit(
                    f"{name} print orientation regressed: "
                    f"height={enclosure_dims[2]:.1f} mm (expected <= 155 mm)"
                )
            if enclosure_dims[1] > 72.0:
                raise SystemExit(
                    f"{name} footprint became unexpectedly deep: "
                    f"depth={enclosure_dims[1]:.1f} mm (expected <= 72 mm)"
                )
            if enclosure_dims[0] > max_width:
                raise SystemExit(
                    f"{name} became unexpectedly wide: "
                    f"width={enclosure_dims[0]:.1f} mm "
                    f"(expected <= {max_width:.1f} mm)"
                )

            print(
                f"OK: {name} print bounds "
                f"{enclosure_dims[0]:.1f} x {enclosure_dims[1]:.1f} x "
                f"{enclosure_dims[2]:.1f} mm"
            )

            assert_no_floating_layer_islands(name, enclosure)

        for preview in (
            "00_CLOSED_ASSEMBLY.scad",
            "00_OPEN_ASSEMBLY.scad",
            "00_TWO_MIDDLE_CLOSED_ASSEMBLY.scad",
            "00_TWO_MIDDLE_OPEN_ASSEMBLY.scad",
            "00_FOUR_PANEL_CLOSED_ASSEMBLY.scad",
            "00_FOUR_PANEL_OPEN_ASSEMBLY.scad",
        ):
            subprocess.run(
                [
                    "openscad",
                    "-o",
                    str(generated_dir / f"{Path(preview).stem}.csg"),
                    str(HINGE_DIR / preview),
                ],
                check=True,
            )
            print(f"OK: {preview}")


if __name__ == "__main__":
    main()
