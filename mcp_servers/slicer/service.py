"""Shared slicer service used by the MCP server.

This layer intentionally calls the same repository scripts used by GitHub
Actions and Codespaces. It does not reimplement Bambu Studio slicing.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
SLICE_SCRIPT = ROOT / "scripts/slicer/slice-stl.sh"
INSTALL_SCRIPT = ROOT / "scripts/slicer/install-bambu-studio.sh"
DEFAULT_MACHINE = "Bambu Lab H2D 0.4 nozzle"
DEFAULT_PROCESS = "0.20mm Standard @BBL H2D"
DEFAULT_FILAMENT = "Bambu PLA Basic @BBL H2D"
DEFAULT_TIMEOUT_SECONDS = 900

ALLOWED_INPUT_ROOTS = (
    (ROOT / "hardware").resolve(),
    (ROOT / "artifacts/slicer-input").resolve(),
)
OUTPUT_ROOT = (ROOT / "artifacts/slicer").resolve()


class SlicerServiceError(RuntimeError):
    """Expected, audit-safe slicer service failure."""


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def _repo_relative(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def _resolve_model(path_value: str) -> Path:
    if not path_value or not str(path_value).strip():
        raise SlicerServiceError("model path is required")

    requested = Path(path_value)
    candidate = requested if requested.is_absolute() else ROOT / requested
    path = candidate.resolve()

    if not any(_is_relative_to(path, root) for root in ALLOWED_INPUT_ROOTS):
        raise SlicerServiceError(
            "model path must be under hardware/ or artifacts/slicer-input/"
        )
    if path.suffix.lower() not in {".stl", ".3mf"}:
        raise SlicerServiceError("model path must end in .stl or .3mf")
    if not path.is_file():
        raise SlicerServiceError(f"model does not exist: {_repo_relative(path)}")
    return path


def _resolve_output(path: Path) -> Path:
    resolved = path.resolve()
    if not _is_relative_to(resolved, OUTPUT_ROOT):
        raise SlicerServiceError("slicer output must remain under artifacts/slicer/")
    return resolved


def _find_slicer() -> Path | None:
    explicit = os.environ.get("SLICER_PATH", "").strip()
    candidates = [
        Path(explicit) if explicit else None,
        ROOT / ".tools/bin/bambu-studio",
        Path("/Applications/BambuStudio.app/Contents/MacOS/BambuStudio"),
        Path("/Applications/Bambu Studio.app/Contents/MacOS/BambuStudio"),
    ]
    for candidate in candidates:
        if candidate and candidate.is_file() and os.access(candidate, os.X_OK):
            return candidate.resolve()
    return None


def _find_profile_root() -> Path | None:
    explicit = os.environ.get("BAMBU_PROFILE_ROOT", "").strip()
    if explicit:
        path = Path(explicit).expanduser().resolve()
        if path.is_dir():
            return path

    tools_root = ROOT / ".tools/bambu-studio"
    if tools_root.is_dir():
        matches = sorted(tools_root.glob("*/app/resources/profiles/BBL"), reverse=True)
        for match in matches:
            if match.is_dir():
                return match.resolve()

    slicer = _find_slicer()
    if slicer and sys.platform == "darwin":
        contents_root = slicer.parents[1]
        candidate = contents_root / "Resources/profiles/BBL"
        if candidate.is_dir():
            return candidate.resolve()
    return None


@dataclass
class BambuStudioProvider:
    """Thin provider over the repository's proven Bambu Studio scripts."""

    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS

    @property
    def name(self) -> str:
        return "bambustudio"

    def capabilities(self) -> dict[str, Any]:
        slicer = _find_slicer()
        profile_root = _find_profile_root()
        return {
            "provider": self.name,
            "available": slicer is not None,
            "executable": _repo_relative(slicer) if slicer else None,
            "profile_root": _repo_relative(profile_root) if profile_root else None,
            "install_script_available": INSTALL_SCRIPT.is_file(),
            "slice_script_available": SLICE_SCRIPT.is_file(),
            "version": os.environ.get("BAMBU_STUDIO_VERSION", "v02.08.02.61"),
            "default_machine_profile": DEFAULT_MACHINE,
            "default_process_profile": DEFAULT_PROCESS,
            "default_filament_profile": DEFAULT_FILAMENT,
            "printer_model": "h2d",
            "printer_handoff_available": False,
        }

    def inspect_model(self, path_value: str) -> dict[str, Any]:
        path = _resolve_model(path_value)
        result: dict[str, Any] = {
            "path": _repo_relative(path),
            "suffix": path.suffix.lower(),
            "size_bytes": path.stat().st_size,
        }

        try:
            import trimesh
        except ImportError as error:
            raise SlicerServiceError(
                "trimesh is required for slicer_inspect_model; install MCP requirements"
            ) from error

        try:
            loaded = trimesh.load(path, process=False)
            if isinstance(loaded, trimesh.Scene):
                if not loaded.geometry:
                    raise SlicerServiceError("model contains no geometry")
                mesh = trimesh.util.concatenate(tuple(loaded.geometry.values()))
            else:
                mesh = loaded
        except SlicerServiceError:
            raise
        except Exception as error:
            raise SlicerServiceError("unable to inspect model geometry") from error

        bounds = mesh.bounds.tolist() if getattr(mesh, "bounds", None) is not None else None
        extents = mesh.extents.tolist() if getattr(mesh, "extents", None) is not None else None
        result.update(
            {
                "vertices": int(len(mesh.vertices)),
                "faces": int(len(mesh.faces)),
                "watertight": bool(mesh.is_watertight),
                "body_count": int(mesh.body_count),
                "bounds_mm": bounds,
                "dimensions_mm": extents,
            }
        )
        return result

    def list_profiles(self, profile_type: str | None = None) -> dict[str, Any]:
        root = _find_profile_root()
        if root is None:
            return {
                "available": False,
                "profile_root": None,
                "profiles": [],
                "message": "Bambu profile root not found; install Bambu Studio first",
            }

        wanted = (profile_type or "").strip().lower()
        if wanted and wanted not in {"machine", "process", "filament"}:
            raise SlicerServiceError(
                "profile_type must be machine, process, filament, or omitted"
            )

        profiles: list[dict[str, str]] = []
        for file_path in root.rglob("*.json"):
            try:
                payload = json.loads(file_path.read_text(encoding="utf-8"))
            except (OSError, UnicodeDecodeError, json.JSONDecodeError):
                continue
            if not isinstance(payload, dict):
                continue
            kind = str(payload.get("type") or "").strip().lower()
            name = str(payload.get("name") or "").strip()
            if kind not in {"machine", "process", "filament"} or not name:
                continue
            if wanted and kind != wanted:
                continue
            # Keep the MCP response bounded and useful for this H2D repository.
            lower_name = name.casefold()
            if "h2d" not in lower_name and kind != "filament":
                continue
            profiles.append(
                {
                    "name": name,
                    "type": kind,
                    "source": _repo_relative(file_path),
                }
            )

        profiles.sort(key=lambda item: (item["type"], item["name"].casefold()))
        return {
            "available": True,
            "profile_root": _repo_relative(root),
            "profiles": profiles[:250],
            "truncated": len(profiles) > 250,
        }

    def slice(
        self,
        path_value: str,
        *,
        machine_profile: str = DEFAULT_MACHINE,
        process_profile: str = DEFAULT_PROCESS,
        filament_profile: str = DEFAULT_FILAMENT,
        orient: bool = False,
        bed_type: str | None = None,
    ) -> dict[str, Any]:
        path = _resolve_model(path_value)
        if not SLICE_SCRIPT.is_file():
            raise SlicerServiceError("shared slicer script is missing")

        output_dir = _resolve_output(
            OUTPUT_ROOT / f"mcp-{path.stem}-{uuid.uuid4().hex[:10]}"
        )
        output_dir.mkdir(parents=True, exist_ok=False)

        env = os.environ.copy()
        env["SLICER_MACHINE_PROFILE"] = machine_profile
        env["SLICER_PROCESS_PROFILE"] = process_profile
        env["SLICER_FILAMENT_PROFILE"] = filament_profile
        env["SLICER_ORIENT"] = "1" if orient else "0"
        if bed_type:
            env["SLICER_BED_TYPE"] = bed_type

        command = [
            "bash",
            str(SLICE_SCRIPT),
            _repo_relative(path),
            str(output_dir),
        ]
        try:
            completed = subprocess.run(
                command,
                cwd=ROOT,
                env=env,
                text=True,
                capture_output=True,
                timeout=self.timeout_seconds,
                check=False,
            )
        except subprocess.TimeoutExpired as error:
            raise SlicerServiceError(
                f"slicing exceeded timeout of {self.timeout_seconds} seconds"
            ) from error

        result_path = output_dir / "result.json"
        if result_path.is_file():
            try:
                result = json.loads(result_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as error:
                raise SlicerServiceError("slicer produced malformed result.json") from error
        else:
            result = {
                "ok": False,
                "categories": ["SLICER_ERROR", "MISSING_OUTPUT"],
                "fatal_categories": ["SLICER_ERROR", "MISSING_OUTPUT"],
                "slicer_exit": completed.returncode,
                "artifact": None,
            }

        result.update(
            {
                "provider": self.name,
                "provider_version": os.environ.get(
                    "BAMBU_STUDIO_VERSION", "v02.08.02.61"
                ),
                "machine_profile": machine_profile,
                "process_profile": process_profile,
                "filament_profile": filament_profile,
                "orient": bool(orient),
                "bed_type": bed_type,
                "output_dir": _repo_relative(output_dir),
                "log": _repo_relative(output_dir / "slicer.log"),
            }
        )

        # Never return the captured raw process output through MCP. The shared
        # script writes a bounded artifact log that can be inspected separately.
        if completed.returncode != 0 and result.get("ok"):
            result["ok"] = False
            result.setdefault("categories", []).append("SLICER_ERROR")
            result.setdefault("fatal_categories", []).append("SLICER_ERROR")
        return result


class SlicerService:
    def __init__(self, provider: BambuStudioProvider | None = None):
        self.provider = provider or BambuStudioProvider()

    def capabilities(self) -> dict[str, Any]:
        return {
            "service": "led-slicer-mcp",
            "providers": [self.provider.capabilities()],
            "allowed_input_roots": [
                _repo_relative(path) for path in ALLOWED_INPUT_ROOTS
            ],
            "output_root": _repo_relative(OUTPUT_ROOT),
            "cloudflare_remote_endpoint": {
                "configured": False,
                "recommended_path_if_deployed": "/mcp/slicer",
                "note": (
                    "No Cloudflare endpoint is required for stdio/Codespaces. "
                    "A permanent cloud-hosted MCP should use a separate protected "
                    "endpoint rather than /api/control/v1/*."
                ),
            },
        }

    def inspect_model(self, path: str) -> dict[str, Any]:
        return self.provider.inspect_model(path)

    def list_profiles(self, profile_type: str | None = None) -> dict[str, Any]:
        return self.provider.list_profiles(profile_type)

    def slice_model(self, **kwargs: Any) -> dict[str, Any]:
        return self.provider.slice(**kwargs)

    def validate_for_print(self, **kwargs: Any) -> dict[str, Any]:
        result = self.provider.slice(**kwargs)
        return {
            **result,
            "validation_only": True,
            "ready_for_print": bool(result.get("ok") and result.get("artifact")),
        }

    def prepare_print(self, **kwargs: Any) -> dict[str, Any]:
        result = self.provider.slice(**kwargs)
        ready = bool(result.get("ok") and result.get("artifact"))
        return {
            **result,
            "ready_for_print": ready,
            "print_started": False,
            "printer_handoff_available": False,
            "next_step": (
                "Pass the pre-sliced artifact to the Bambu printer provider"
                if ready
                else "Resolve slicer validation failures before printer handoff"
            ),
        }
