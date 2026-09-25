#!/usr/bin/env python3
"""Regenerate hinge prototype v2 STLs and verify checked-in meshes are current."""

from __future__ import annotations

import hashlib
import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
HINGE_DIR = ROOT / "hardware/enclosure/direct-mount/hinge-prototype-v2"

PARTS = {
    "01_moving_panel_template_HINGE_TEST.scad":
        "01_moving_panel_template_HINGE_TEST.stl",
    "02_middle_stationary_enclosure_HINGE_TEST.scad":
        "02_middle_stationary_enclosure_HINGE_TEST.stl",
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

        enclosure = generated_dir / PARTS[
            "02_middle_stationary_enclosure_HINGE_TEST.scad"
        ]
        enclosure_dims = assert_on_bed("middle stationary enclosure", enclosure)

        # The tapered middle enclosure now prints upright on its real floor base:
        # X ~= 255 mm, Y ~= 68 mm total front/rear footprint, Z ~= 148 mm.
        if enclosure_dims[2] > 155.0:
            raise SystemExit(
                "middle stationary enclosure print orientation regressed: "
                f"height={enclosure_dims[2]:.1f} mm (expected <= 155 mm)"
            )
        if enclosure_dims[1] > 72.0:
            raise SystemExit(
                "middle stationary enclosure footprint became unexpectedly deep: "
                f"depth={enclosure_dims[1]:.1f} mm (expected <= 72 mm)"
            )

        print(
            "OK: moving template print bounds "
            f"{template_dims[0]:.1f} x {template_dims[1]:.1f} x {template_dims[2]:.1f} mm"
        )
        print(
            "OK: middle enclosure print bounds "
            f"{enclosure_dims[0]:.1f} x {enclosure_dims[1]:.1f} x {enclosure_dims[2]:.1f} mm"
        )

        for preview in (
            "00_CLOSED_ASSEMBLY.scad",
            "00_OPEN_ASSEMBLY.scad",
            "00_TWO_MIDDLE_CLOSED_ASSEMBLY.scad",
            "00_TWO_MIDDLE_OPEN_ASSEMBLY.scad",
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
