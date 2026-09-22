#!/usr/bin/env python3
"""Validate generated enclosure meshes and nominal assembly interfaces.

STL files contain triangles, not mate/assembly intent.  This checker combines
the checked-in meshes with explicit transforms and interface expectations from
assembly_validation.json, then tests the resulting nominal assembly.

Known unresolved mechanical findings can be marked expected_failure in the
manifest.  They are reported as XFAIL/XPASS but do not hide failures in
interfaces that are expected to fit today.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np
import trimesh


AXES = {"x": 0, "y": 1, "z": 2}


def as_mesh(loaded: trimesh.Trimesh | trimesh.Scene, source: str) -> trimesh.Trimesh:
    if isinstance(loaded, trimesh.Scene):
        if not loaded.geometry:
            raise ValueError(f"{source}: scene contains no geometry")
        loaded = trimesh.util.concatenate(tuple(loaded.geometry.values()))
    if not isinstance(loaded, trimesh.Trimesh):
        raise TypeError(f"{source}: unsupported geometry type {type(loaded)!r}")
    return loaded


def load_mesh(path: Path) -> trimesh.Trimesh:
    return as_mesh(trimesh.load_mesh(path, process=True), str(path))


def primitive_mesh(spec: dict) -> trimesh.Trimesh:
    kind = spec["type"]
    if kind != "cylinder":
        raise ValueError(f"Unsupported primitive type: {kind}")

    mesh = trimesh.creation.cylinder(
        radius=float(spec["radius"]),
        height=float(spec["height"]),
        sections=int(spec.get("sections", 96)),
    )

    axis = spec.get("axis", "z")
    if axis == "x":
        mesh.apply_transform(
            trimesh.transformations.rotation_matrix(math.pi / 2.0, [0, 1, 0])
        )
    elif axis == "y":
        mesh.apply_transform(
            trimesh.transformations.rotation_matrix(math.pi / 2.0, [1, 0, 0])
        )
    elif axis != "z":
        raise ValueError(f"Unsupported cylinder axis: {axis}")

    mesh.apply_translation(np.asarray(spec["center"], dtype=float))
    return mesh


def intersection_volume(a: trimesh.Trimesh, b: trimesh.Trimesh) -> float:
    result = trimesh.boolean.intersection(
        [a, b],
        engine="manifold",
        check_volume=True,
    )
    if result is None:
        return 0.0
    result = as_mesh(result, "boolean intersection")
    if result.is_empty:
        return 0.0
    return abs(float(result.volume))


def check_mesh_health(name: str, mesh: trimesh.Trimesh) -> list[str]:
    errors: list[str] = []
    if mesh.is_empty:
        errors.append("mesh is empty")
        return errors
    if not np.isfinite(mesh.vertices).all():
        errors.append("mesh contains non-finite vertices")
    if not mesh.is_watertight:
        errors.append("mesh is not watertight")
    if not mesh.is_winding_consistent:
        errors.append("mesh winding is inconsistent")
    if not mesh.is_volume:
        errors.append("mesh is not a valid closed volume")
    if np.any(mesh.extents <= 0):
        errors.append(f"mesh has non-positive extents {mesh.extents.tolist()}")
    return errors


def result_line(ok: bool, expected_failure: bool, label: str, detail: str) -> str:
    if expected_failure:
        state = "XPASS" if ok else "XFAIL"
    else:
        state = "PASS" if ok else "FAIL"
    return f"{state:5} {label}: {detail}"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "manifest",
        type=Path,
        nargs="?",
        default=Path(__file__).with_name("assembly_validation.json"),
    )
    args = parser.parse_args()

    manifest_path = args.manifest.resolve()
    root = manifest_path.parent
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    failures = 0
    parts: dict[str, trimesh.Trimesh] = {}

    print("Mesh health")
    print("-----------")
    for part_name, spec in manifest["parts"].items():
        path = root / spec["file"]
        if not path.exists():
            print(f"FAIL  {part_name}: missing {path.name}")
            failures += 1
            continue

        mesh = load_mesh(path)
        parts[part_name] = mesh
        errors = check_mesh_health(part_name, mesh)
        extents = " x ".join(f"{value:.3f}" for value in mesh.extents)
        if errors:
            print(f"FAIL  {part_name}: {'; '.join(errors)}")
            failures += 1
        else:
            print(f"PASS  {part_name}: {extents} mm, {len(mesh.faces)} triangles")

    if failures:
        print(f"\nStopping before assembly checks: {failures} mesh-health failure(s).")
        return 1

    instances: dict[str, trimesh.Trimesh] = {}
    translations: dict[str, np.ndarray] = {}
    for instance_name, spec in manifest.get("instances", {}).items():
        translation = np.asarray(spec.get("translate", [0, 0, 0]), dtype=float)
        mesh = parts[spec["part"]].copy()
        mesh.apply_translation(translation)
        instances[instance_name] = mesh
        translations[instance_name] = translation

    for primitive_name, spec in manifest.get("primitives", {}).items():
        instances[primitive_name] = primitive_mesh(spec)

    layout_checks = manifest.get("layout_checks", [])
    if layout_checks:
        print("\nAssembly placement / alignment")
        print("------------------------------")
        for check in layout_checks:
            kind = check["type"]
            label = check["name"]
            tolerance = float(check.get("tolerance_mm", 0.01))

            try:
                if kind == "translation_equals":
                    actual = translations[check["instance"]]
                    expected = np.asarray(check["value"], dtype=float)
                    delta = np.abs(actual - expected)
                    ok = bool(np.all(delta <= tolerance))
                    detail = (
                        f"{check['instance']} translation={actual.tolist()}, "
                        f"expected={expected.tolist()}, max delta={float(delta.max()):.6f} mm"
                    )
                elif kind == "translation_axis_equal":
                    axis_name = check["axis"]
                    axis = AXES[axis_name]
                    expected = float(check["value"])
                    values = [float(translations[name][axis]) for name in check["instances"]]
                    deltas = [abs(value - expected) for value in values]
                    ok = all(delta <= tolerance for delta in deltas)
                    detail = (
                        f"{axis_name} values={values}, expected={expected:.3f}, "
                        f"max delta={max(deltas, default=0.0):.6f} mm"
                    )
                elif kind == "translation_sequence":
                    axis_name = check["axis"]
                    axis = AXES[axis_name]
                    start = float(check["start"])
                    step = float(check["step"])
                    values = [float(translations[name][axis]) for name in check["instances"]]
                    expected = [start + step * index for index in range(len(values))]
                    deltas = [abs(a - b) for a, b in zip(values, expected)]
                    ok = all(delta <= tolerance for delta in deltas)
                    detail = (
                        f"{axis_name} values={values}, expected={expected}, "
                        f"max delta={max(deltas, default=0.0):.6f} mm"
                    )
                else:
                    raise ValueError(f"Unsupported layout check type: {kind}")
            except Exception as exc:
                ok = False
                detail = f"check raised {type(exc).__name__}: {exc}"

            print(result_line(ok, False, label, detail))
            if not ok:
                failures += 1

    print("\nAssembly interfaces")
    print("-------------------")
    for check in manifest.get("checks", []):
        kind = check["type"]
        label = check["name"]
        expected_failure = bool(check.get("expected_failure", False))
        issue = check.get("issue")
        suffix = f" [{issue}]" if issue else ""

        try:
            if kind == "no_interference":
                volume = intersection_volume(
                    instances[check["a"]],
                    instances[check["b"]],
                )
                limit = float(check.get("max_intersection_mm3", 0.01))
                ok = volume <= limit
                detail = (
                    f"{check['a']} vs {check['b']} intersection "
                    f"{volume:.6f} mm^3 (limit {limit:.6f}){suffix}"
                )
            elif kind == "axis_bounds":
                axis_name = check["axis"]
                axis = AXES[axis_name]
                selected = [instances[name] for name in check["instances"]]
                actual_min = min(float(mesh.bounds[0, axis]) for mesh in selected)
                actual_max = max(float(mesh.bounds[1, axis]) for mesh in selected)
                required_min = float(check["min"])
                required_max = float(check["max"])
                tolerance = float(check.get("tolerance_mm", 0.01))
                ok = (
                    actual_min >= required_min - tolerance
                    and actual_max <= required_max + tolerance
                )
                detail = (
                    f"{axis_name}={actual_min:.3f}..{actual_max:.3f} mm, "
                    f"required {required_min:.3f}..{required_max:.3f} mm{suffix}"
                )
            else:
                raise ValueError(f"Unsupported check type: {kind}")
        except Exception as exc:
            ok = False
            detail = f"check raised {type(exc).__name__}: {exc}{suffix}"

        print(result_line(ok, expected_failure, label, detail))
        if not ok and not expected_failure:
            failures += 1

    manual = manifest.get("manual_validation_gates", [])
    if manual:
        print("\nManual / physical validation still required")
        print("-------------------------------------------")
        for item in manual:
            issue = f" [{item['issue']}]" if item.get("issue") else ""
            print(f"MANUAL {item['name']}: {item['reason']}{issue}")

    print()
    if failures:
        print(f"Mechanical validation failed: {failures} required check(s) failed.")
        return 1

    print("Mechanical validation passed for all required automated checks.")
    print("XFAIL entries are tracked known issues, not proof of compatibility.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
