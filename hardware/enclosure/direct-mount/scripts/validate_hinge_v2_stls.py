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
    "01_fixed_template_HINGE_TEST.scad": "01_fixed_template_HINGE_TEST.stl",
    "02_moving_enclosure_HINGE_TEST.scad": "02_moving_enclosure_HINGE_TEST.stl",
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

        moving = generated_dir / PARTS["02_moving_enclosure_HINGE_TEST.scad"]
        mins, maxs = bounds(moving)
        dims = tuple(maxs[i] - mins[i] for i in range(3))

        if abs(mins[2]) > 0.05:
            raise SystemExit(
                f"moving enclosure does not sit on print Z=0: min_z={mins[2]:.3f}"
            )
        if dims[2] > 30.0:
            raise SystemExit(
                "moving enclosure print orientation regressed: "
                f"height={dims[2]:.1f} mm (expected <= 30 mm)"
            )

        print(
            "OK: moving enclosure print bounds "
            f"{dims[0]:.1f} x {dims[1]:.1f} x {dims[2]:.1f} mm"
        )

        for preview in ("00_CLOSED_ASSEMBLY.scad", "00_OPEN_ASSEMBLY.scad"):
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
