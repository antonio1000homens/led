#!/usr/bin/env python3
"""Select bounded slicer targets for manual or PR-triggered validation."""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ALLOWED_ROOT = (ROOT / "hardware/enclosure").resolve()


def safe_model(value: str) -> Path:
    candidate = Path(value)
    if not candidate.is_absolute():
        candidate = ROOT / candidate
    path = candidate.resolve()
    try:
        path.relative_to(ALLOWED_ROOT)
    except ValueError as exc:
        raise ValueError("target must be under hardware/enclosure") from exc
    if path.suffix.lower() not in {".stl", ".3mf"}:
        raise ValueError("target must be an STL or 3MF")
    if not path.is_file():
        raise ValueError(f"target does not exist: {path.relative_to(ROOT)}")
    return path


def git_changed(base: str, head: str) -> list[str]:
    result = subprocess.run(
        ["git", "diff", "--name-only", f"{base}...{head}"],
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=True,
    )
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def from_changed(paths: list[str]) -> list[Path]:
    selected: set[Path] = set()
    for value in paths:
        path = Path(value)
        lower = path.suffix.lower()
        if lower in {".stl", ".3mf"} and value.startswith("hardware/enclosure/"):
            try:
                selected.add(safe_model(value))
            except ValueError:
                pass
            continue

        # Printable wrappers map 1:1 to their tracked manufacturing STL.
        if (
            lower == ".scad"
            and "hardware/enclosure/direct-mount/parts/" in value
        ):
            mapped = (
                ROOT
                / "hardware/enclosure/direct-mount/stl"
                / f"{path.stem}.stl"
            )
            if mapped.is_file():
                selected.add(mapped.resolve())
            continue

        if (
            lower == ".scad"
            and "hardware/enclosure/direct-mount/hinge-prototype-v2/" in value
            and path.name.endswith("_HINGE_TEST.scad")
        ):
            mapped = path.parent / "stl" / f"{path.stem}.stl"
            absolute = (ROOT / mapped).resolve()
            if absolute.is_file():
                selected.add(absolute)

    return sorted(selected)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--explicit")
    parser.add_argument("--base")
    parser.add_argument("--head", default="HEAD")
    parser.add_argument("--max-targets", type=int, default=4)
    args = parser.parse_args()

    if args.max_targets < 1:
        raise SystemExit("--max-targets must be at least 1")

    if args.explicit:
        models = [safe_model(args.explicit)]
    elif args.base:
        models = from_changed(git_changed(args.base, args.head))
    else:
        raise SystemExit("provide --explicit or --base")

    if not models:
        print("No slicable STL/3MF targets selected.")
        return

    if len(models) > args.max_targets:
        rels = [str(path.relative_to(ROOT)) for path in models]
        raise SystemExit(
            "Full slicing would process "
            f"{len(models)} models, exceeding max-targets={args.max_targets}. "
            "Use workflow_dispatch with an explicit stl_path, or raise the "
            "limit deliberately.\n" + "\n".join(rels)
        )

    for path in models:
        print(path.relative_to(ROOT))


if __name__ == "__main__":
    main()
