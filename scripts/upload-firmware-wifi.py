#!/usr/bin/env python3
"""Upload the staged MatrixPortal application through CircuitPython Web Workflow."""

from __future__ import annotations

import argparse
import base64
import getpass
import hashlib
from pathlib import Path
import subprocess
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urljoin
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STAGE = ROOT / ".build" / "circuitpy"


def staged_files(stage: Path) -> list[Path]:
    """Return only regular application files, with code.py uploaded last."""
    files = sorted(path for path in stage.iterdir() if path.is_file() and path.name != "code.py")
    code = stage / "code.py"
    if code.is_file():
        files.append(code)
    if not files:
        raise ValueError(f"No staged application files found in {stage}")
    return files


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class WebWorkflowClient:
    def __init__(self, host: str, password: str, opener=urlopen):
        self.base = host.rstrip("/") + "/"
        self.auth = "Basic " + base64.b64encode((":" + password).encode()).decode("ascii")
        self.opener = opener

    def request(self, method: str, path: str, data: bytes | None = None):
        url = urljoin(self.base, "fs/" + quote(path.lstrip("/"), safe="/"))
        request = Request(url, data=data, method=method, headers={"Authorization": self.auth})
        return self.opener(request, timeout=30)

    def upload(self, relative_path: str, data: bytes) -> None:
        with self.request("PUT", relative_path, data=data) as response:
            if response.status not in (201, 204):
                raise RuntimeError(f"upload failed for {relative_path}: HTTP {response.status}")

    def download(self, relative_path: str) -> bytes:
        with self.request("GET", relative_path) as response:
            if response.status != 200:
                raise RuntimeError(f"readback failed for {relative_path}: HTTP {response.status}")
            return response.read()


def stage_application(stage: Path) -> None:
    subprocess.run(["bash", str(ROOT / "scripts" / "stage-firmware.sh"), str(stage)], check=True)


def upload(stage: Path, client: WebWorkflowClient) -> list[str]:
    uploaded = []
    for path in staged_files(stage):
        relative = path.name
        content = path.read_bytes()
        client.upload(relative, content)
        if digest(client.download(relative)) != digest(content):
            raise RuntimeError(f"readback hash mismatch for {relative}")
        uploaded.append(relative)
    return uploaded


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="http://matrixportal-s3.local", help="Board URL or http://host")
    parser.add_argument("--stage-dir", type=Path, default=DEFAULT_STAGE)
    parser.add_argument("--skip-stage", action="store_true", help="Use an existing staged directory")
    args = parser.parse_args(argv)
    host = args.host if "://" in args.host else "http://" + args.host
    password = getpass.getpass("CircuitPython Web Workflow password: ")
    try:
        if not args.skip_stage:
            stage_application(args.stage_dir)
        names = upload(args.stage_dir, WebWorkflowClient(host, password))
    except (HTTPError, URLError, OSError, RuntimeError, ValueError, subprocess.CalledProcessError) as exc:
        detail = getattr(exc, "code", None)
        if detail == 409:
            print("Upload refused: USB CIRCUITPY storage is active. Eject it, then retry.", file=sys.stderr)
        elif detail in (401, 403):
            print("Upload refused: check the Web Workflow password and board address.", file=sys.stderr)
        else:
            print(f"Upload failed: {exc}", file=sys.stderr)
        print("Leave the board paused and retry; use USB recovery if Wi-Fi is unavailable.", file=sys.stderr)
        return 1
    print(f"Uploaded and verified {len(names)} application files to {host}")
    print("Press Ctrl-D in the Web Workflow serial console to return to standard mode.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
