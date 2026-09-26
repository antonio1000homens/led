"""Cloud workspace management for the slicer MCP.

Workspaces are detached git worktrees at immutable commits. Generated meshes are
written back into the repository's existing artifacts/slicer-input allowlist so
that the proven Bambu Studio provider can slice them without gaining arbitrary
filesystem access.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REPOSITORY = "antonio1000homens/led"
WORKSPACE_ID_RE = re.compile(r"^[0-9a-f]{12}$")
COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")


class WorkspaceError(RuntimeError):
    """Expected, audit-safe workspace failure."""


@dataclass(frozen=True)
class Workspace:
    workspace_id: str
    commit: str
    path: Path


class WorkspaceManager:
    def __init__(
        self,
        *,
        root: Path = ROOT,
        workspace_root: Path | None = None,
        timeout_seconds: int = 120,
    ):
        self.root = root.resolve()
        configured = os.environ.get("SLICER_WORKSPACE_ROOT", "").strip()
        default_root = self.root.parent / ".led-slicer-workspaces"
        self.workspace_root = (
            Path(configured).expanduser()
            if configured
            else (workspace_root or default_root)
        ).resolve()
        self.timeout_seconds = timeout_seconds

    @property
    def repository(self) -> str:
        return os.environ.get(
            "SLICER_REPOSITORY_FULL_NAME", DEFAULT_REPOSITORY
        ).strip() or DEFAULT_REPOSITORY

    def _run(
        self,
        args: list[str],
        *,
        cwd: Path | None = None,
        timeout: int | None = None,
    ) -> subprocess.CompletedProcess[str]:
        try:
            completed = subprocess.run(
                args,
                cwd=cwd or self.root,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=timeout or self.timeout_seconds,
                check=False,
            )
        except subprocess.TimeoutExpired as error:
            raise WorkspaceError("workspace command timed out") from error
        return completed

    def _git(self, *args: str, cwd: Path | None = None) -> str:
        completed = self._run(["git", *args], cwd=cwd)
        if completed.returncode != 0:
            raise WorkspaceError("git workspace operation failed")
        return completed.stdout.strip()

    def _ensure_commit(self, commit: str) -> str:
        normalized = commit.strip().lower()
        if not COMMIT_RE.fullmatch(normalized):
            raise WorkspaceError("commit must be a full 40-character SHA")

        probe = self._run(["git", "cat-file", "-e", f"{normalized}^{{commit}}"])
        if probe.returncode != 0:
            fetched = self._run(
                ["git", "fetch", "--no-tags", "--depth=1", "origin", normalized],
                timeout=max(self.timeout_seconds, 180),
            )
            if fetched.returncode != 0:
                raise WorkspaceError("requested commit is not available from origin")
            probe = self._run(["git", "cat-file", "-e", f"{normalized}^{{commit}}"])
            if probe.returncode != 0:
                raise WorkspaceError("requested commit is not a valid git commit")

        resolved = self._git("rev-parse", f"{normalized}^{{commit}}").lower()
        if resolved != normalized:
            raise WorkspaceError("resolved commit does not match request")
        return resolved

    def prepare(self, *, repository: str, commit: str) -> dict[str, Any]:
        if repository.strip() != self.repository:
            raise WorkspaceError(
                f"repository must be {self.repository}"
            )
        resolved = self._ensure_commit(commit)
        workspace_id = resolved[:12]
        path = (self.workspace_root / workspace_id).resolve()
        if path.parent != self.workspace_root:
            raise WorkspaceError("invalid workspace path")

        self.workspace_root.mkdir(parents=True, exist_ok=True)
        reused = False
        if path.exists():
            try:
                existing = self._git("-C", str(path), "rev-parse", "HEAD").lower()
            except WorkspaceError:
                existing = ""
            if existing == resolved:
                reused = True
            else:
                self._run(["git", "worktree", "remove", "--force", str(path)])
                shutil.rmtree(path, ignore_errors=True)

        if not reused:
            added = self._run(
                ["git", "worktree", "add", "--detach", str(path), resolved],
                timeout=max(self.timeout_seconds, 180),
            )
            if added.returncode != 0:
                raise WorkspaceError("unable to create isolated git worktree")

        return {
            "ok": True,
            "repository": self.repository,
            "commit": resolved,
            "workspace": workspace_id,
            "reused": reused,
        }

    def resolve(self, workspace_id: str) -> Workspace:
        normalized = workspace_id.strip().lower()
        if not WORKSPACE_ID_RE.fullmatch(normalized):
            raise WorkspaceError("workspace must be a 12-character commit identifier")
        path = (self.workspace_root / normalized).resolve()
        if path.parent != self.workspace_root or not path.is_dir():
            raise WorkspaceError("workspace does not exist")
        commit = self._git("-C", str(path), "rev-parse", "HEAD").lower()
        if not COMMIT_RE.fullmatch(commit) or not commit.startswith(normalized):
            raise WorkspaceError("workspace commit identity is invalid")
        return Workspace(normalized, commit, path)

    def generate_model(
        self,
        *,
        workspace_id: str,
        source_path: str,
        output_name: str | None = None,
    ) -> dict[str, Any]:
        workspace = self.resolve(workspace_id)
        requested = Path(source_path)
        if requested.is_absolute():
            raise WorkspaceError("source path must be repository-relative")
        source = (workspace.path / requested).resolve()
        allowed_source = (workspace.path / "hardware/enclosure").resolve()
        try:
            source.relative_to(allowed_source)
        except ValueError as error:
            raise WorkspaceError("source path must be under hardware/enclosure/") from error
        if source.suffix.lower() != ".scad":
            raise WorkspaceError("source path must be an OpenSCAD .scad file")
        if not source.is_file():
            raise WorkspaceError("OpenSCAD source does not exist")

        name = output_name.strip() if output_name else source.with_suffix(".stl").name
        if Path(name).name != name or not name.lower().endswith(".stl"):
            raise WorkspaceError("output_name must be a simple .stl filename")
        if not re.fullmatch(r"[A-Za-z0-9._-]+\.stl", name):
            raise WorkspaceError("output_name contains unsupported characters")

        openscad = shutil.which("openscad")
        if not openscad:
            raise WorkspaceError("OpenSCAD is not installed")

        output_dir = (
            self.root / "artifacts/slicer-input" / workspace.workspace_id
        ).resolve()
        allowed_output_root = (self.root / "artifacts/slicer-input").resolve()
        try:
            output_dir.relative_to(allowed_output_root)
        except ValueError as error:
            raise WorkspaceError("generated model output escaped allowlist") from error
        output_dir.mkdir(parents=True, exist_ok=True)
        output = output_dir / name

        started = time.monotonic()
        completed = self._run(
            [openscad, "-o", str(output), str(source)],
            cwd=workspace.path,
            timeout=int(os.environ.get("SLICER_GENERATE_TIMEOUT_SECONDS", "300")),
        )
        elapsed = time.monotonic() - started
        if completed.returncode != 0:
            raise WorkspaceError("OpenSCAD generation failed")
        if not output.is_file() or output.stat().st_size == 0:
            raise WorkspaceError("OpenSCAD did not produce a non-empty STL")

        return {
            "ok": True,
            "workspace": workspace.workspace_id,
            "commit": workspace.commit,
            "source": str(requested),
            "path": str(output.relative_to(self.root)),
            "size_bytes": output.stat().st_size,
            "generation_seconds": round(elapsed, 3),
        }

    def require_generated_model(self, workspace_id: str, path_value: str) -> Workspace:
        workspace = self.resolve(workspace_id)
        path = (self.root / path_value).resolve()
        expected = (
            self.root / "artifacts/slicer-input" / workspace.workspace_id
        ).resolve()
        try:
            path.relative_to(expected)
        except ValueError as error:
            raise WorkspaceError(
                "workspace slicing requires a generated model from that workspace"
            ) from error
        return workspace
