"""MCP entry point for the LED slicer service."""

from __future__ import annotations

import os
from typing import Any

from mcp.server import MCPServer

from mcp_servers.slicer.service import (
    DEFAULT_FILAMENT,
    DEFAULT_MACHINE,
    DEFAULT_PROCESS,
    SlicerService,
    SlicerServiceError,
)


mcp = MCPServer(
    "LED Slicer",
    version="0.1.0",
    instructions=(
        "Use these tools to inspect and slice LED repository STL/3MF files. "
        "Slicing never starts a printer job."
    ),
)
service = SlicerService()


def _safe_call(callable_, *args, **kwargs) -> dict[str, Any]:
    try:
        return callable_(*args, **kwargs)
    except SlicerServiceError as error:
        return {"ok": False, "error": str(error)}


@mcp.tool()
def slicer_capabilities() -> dict[str, Any]:
    """Report available slicer providers, defaults and remote-access posture."""
    return service.capabilities()


@mcp.tool()
def slicer_inspect_model(path: str) -> dict[str, Any]:
    """Inspect one STL/3MF under the repository's allowed input roots."""
    return _safe_call(service.inspect_model, path)


@mcp.tool()
def slicer_list_profiles(profile_type: str | None = None) -> dict[str, Any]:
    """List available H2D-oriented Bambu machine/process/filament profiles."""
    return _safe_call(service.list_profiles, profile_type)


@mcp.tool()
def slicer_slice(
    path: str,
    machine_profile: str = DEFAULT_MACHINE,
    process_profile: str = DEFAULT_PROCESS,
    filament_profile: str = DEFAULT_FILAMENT,
    orient: bool = False,
    bed_type: str | None = None,
) -> dict[str, Any]:
    """Slice one model with the shared BambuStudio pipeline."""
    return _safe_call(
        service.slice_model,
        path_value=path,
        machine_profile=machine_profile,
        process_profile=process_profile,
        filament_profile=filament_profile,
        orient=orient,
        bed_type=bed_type,
    )


@mcp.tool()
def slicer_validate_for_print(
    path: str,
    machine_profile: str = DEFAULT_MACHINE,
    process_profile: str = DEFAULT_PROCESS,
    filament_profile: str = DEFAULT_FILAMENT,
    orient: bool = False,
    bed_type: str | None = None,
) -> dict[str, Any]:
    """Run a real slice and return a printability result without printing."""
    return _safe_call(
        service.validate_for_print,
        path_value=path,
        machine_profile=machine_profile,
        process_profile=process_profile,
        filament_profile=filament_profile,
        orient=orient,
        bed_type=bed_type,
    )


@mcp.tool()
def slicer_prepare_print(
    path: str,
    machine_profile: str = DEFAULT_MACHINE,
    process_profile: str = DEFAULT_PROCESS,
    filament_profile: str = DEFAULT_FILAMENT,
    orient: bool = False,
    bed_type: str | None = None,
) -> dict[str, Any]:
    """Generate a validated pre-sliced artifact; never start the printer."""
    return _safe_call(
        service.prepare_print,
        path_value=path,
        machine_profile=machine_profile,
        process_profile=process_profile,
        filament_profile=filament_profile,
        orient=orient,
        bed_type=bed_type,
    )


def main() -> None:
    transport = os.environ.get("SLICER_MCP_TRANSPORT", "stdio").strip().lower()
    if transport == "stdio":
        mcp.run()
        return
    if transport == "streamable-http":
        host = os.environ.get("SLICER_MCP_HOST", "127.0.0.1")
        port = int(os.environ.get("SLICER_MCP_PORT", "8000"))
        path = os.environ.get("SLICER_MCP_PATH", "/mcp")
        mcp.run(
            transport="streamable-http",
            host=host,
            port=port,
            streamable_http_path=path,
            json_response=True,
            stateless_http=True,
        )
        return
    raise SystemExit(
        "SLICER_MCP_TRANSPORT must be 'stdio' or 'streamable-http'"
    )


if __name__ == "__main__":
    main()
