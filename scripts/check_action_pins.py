#!/usr/bin/env python3
"""Reject mutable external uses refs in GitHub Actions workflows and composite actions.

The guard checks SHA syntax and readable version comments. Verify the SHA's
upstream provenance manually when adding or reviewing an action.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path


USES_LINE = re.compile(r"^\s*(?:-\s*)?uses\s*:\s*(\S+)(.*)$")
COMMIT_REF = re.compile(r"^[^/@\s]+/[^@\s]+@[0-9a-f]{40}$")
DOCKER_DIGEST = re.compile(r"^docker://[^\s@]+@sha256:[0-9a-f]{64}$")
VERSION_COMMENT = re.compile(r"^\s*#\s*v\d+(?:\.\d+){0,3}\b", re.IGNORECASE)


def action_files(root: Path) -> list[Path]:
    """Find all workflows and locally defined composite actions."""
    github = root / ".github"
    paths: set[Path] = set()
    for pattern in ("workflows/**/*.yml", "workflows/**/*.yaml",
                    "actions/**/action.yml", "actions/**/action.yaml"):
        paths.update(github.glob(pattern))
    paths.update(root.glob("**/action.yml"))
    paths.update(root.glob("**/action.yaml"))
    return sorted(p for p in paths if p.is_file()
                  and not any(part in (".git", ".build", ".venv", "node_modules")
                              for part in p.relative_to(root).parts))


def check_action_references(root: Path) -> list[tuple[str, int, str]]:
    """Return (path, line, problem) for invalid external uses references."""
    failures: list[tuple[str, int, str]] = []
    for path in action_files(root):
        relative = path.relative_to(root).as_posix()
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if line.lstrip().startswith("#"):
                continue
            found = USES_LINE.match(line)
            if not found:
                continue
            action, comment = found.groups()
            action = action.strip("\"'")
            if action.startswith("./"):
                continue  # Local checked-out actions need no external commit pin.
            if not (COMMIT_REF.fullmatch(action) or DOCKER_DIGEST.fullmatch(action)):
                failures.append((relative, number,
                                 "External 'uses' must pin a full 40-character "
                                 "commit SHA (or a Docker sha256 digest), not a tag/branch"))
            elif not VERSION_COMMENT.match(comment):
                failures.append((relative, number,
                                 "External pinned action needs a readable '# vN' "
                                 "version comment"))
    return failures


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    failures = check_action_references(root)
    for path, line, problem in failures:
        print(f"::error file={path},line={line}::{problem}")
    if failures:
        print(f"Failed: {len(failures)} unsafe/missing action pins")
        return 1
    print(f"OK: SHA-pinned external uses references in "
          f"{len(action_files(root))} workflow/action files")
    return 0


if __name__ == "__main__":
    sys.exit(main())
