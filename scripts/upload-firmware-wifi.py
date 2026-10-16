#!/usr/bin/env python3
"""Upload the staged MatrixPortal application through CircuitPython Web Workflow."""

from __future__ import annotations

import argparse
import base64
import getpass
import hashlib
from pathlib import Path
import secrets
import socket
import subprocess
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urljoin
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STAGE = ROOT / ".build" / "circuitpy"
TEMPORARY_BOOT_PY = b"import storage\nstorage.disable_usb_drive()\n"


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


class WebWorkflowSerial:
    """Read CircuitPython's serial WebSocket without exposing its password."""

    def __init__(self, host: str, password: str):
        from urllib.parse import urlsplit

        parsed = urlsplit(host)
        if parsed.scheme != "http" or not parsed.hostname:
            raise ValueError("serial capture requires an http:// board host")
        self.host = parsed.hostname
        self.port = parsed.port or 80
        self.socket = socket.create_connection((self.host, self.port), timeout=10)
        self.socket.settimeout(1)
        auth = base64.b64encode((":" + password).encode()).decode("ascii")
        key = base64.b64encode(secrets.token_bytes(16)).decode("ascii")
        request = (
            "GET /cp/serial/ HTTP/1.1\r\n"
            f"Host: {self.host}\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {key}\r\n"
            "Sec-WebSocket-Version: 13\r\n"
            f"Authorization: Basic {auth}\r\n"
            f"Origin: http://{self.host}\r\n\r\n"
        )
        self.socket.sendall(request.encode("ascii"))
        response = bytearray()
        while b"\r\n\r\n" not in response:
            chunk = self.socket.recv(1)
            if not chunk:
                self.socket.close()
                raise RuntimeError("serial WebSocket closed during handshake")
            response.extend(chunk)
        if b" 101 " not in response.split(b"\r\n", 1)[0]:
            self.socket.close()
            raise RuntimeError("serial WebSocket authentication or upgrade failed")
        self.buffer = bytearray(response.split(b"\r\n\r\n", 1)[1])

    def send_text(self, payload: bytes) -> None:
        mask = secrets.token_bytes(4)
        size = len(payload)
        if size < 126:
            header = bytes((0x81, 0x80 | size))
        elif size <= 0xFFFF:
            header = bytes((0x81, 0xFE)) + size.to_bytes(2, "big")
        else:
            header = bytes((0x81, 0xFF)) + size.to_bytes(8, "big")
        masked = bytes(value ^ mask[index & 3] for index, value in enumerate(payload))
        self.socket.sendall(header + mask + masked)

    def read_text(self, timeout: float) -> list[str]:
        end = time.monotonic() + timeout
        messages = []
        while time.monotonic() < end:
            try:
                self.buffer.extend(self.socket.recv(4096))
            except socket.timeout:
                continue
            except OSError:
                break
            while len(self.buffer) >= 2:
                first, second = self.buffer[0], self.buffer[1]
                size = second & 0x7F
                offset = 2
                if size == 126:
                    if len(self.buffer) < 4:
                        break
                    size = int.from_bytes(self.buffer[2:4], "big")
                    offset = 4
                elif size == 127:
                    if len(self.buffer) < 10:
                        break
                    size = int.from_bytes(self.buffer[2:10], "big")
                    offset = 10
                mask = None
                if second & 0x80:
                    if len(self.buffer) < offset + 4:
                        break
                    mask = self.buffer[offset:offset + 4]
                    offset += 4
                if len(self.buffer) < offset + size:
                    break
                payload = bytes(self.buffer[offset:offset + size])
                del self.buffer[:offset + size]
                if mask:
                    payload = bytes(value ^ mask[index & 3]
                                    for index, value in enumerate(payload))
                opcode = first & 0x0F
                if opcode == 1:
                    messages.append(payload.decode("utf-8", "replace"))
                elif opcode == 8:
                    return messages
        return messages

    def close(self) -> None:
        self.socket.close()


def stage_application(stage: Path) -> None:
    subprocess.run(["bash", str(ROOT / "scripts" / "stage-firmware.sh"), str(stage)], check=True)


def upload(stage: Path, client: WebWorkflowClient) -> list[str]:
    """Upload a complete staged payload.

    PUTs are intentionally repeatable: after an interrupted run the operator can
    leave the board paused and run this function/helper again. Existing remote
    files are overwritten and each successful PUT is verified by SHA-256
    readback before moving on.
    """
    uploaded = []
    for path in staged_files(stage):
        relative = path.name
        content = path.read_bytes()
        client.upload(relative, content)
        if digest(client.download(relative)) != digest(content):
            raise RuntimeError(f"readback hash mismatch for {relative}")
        uploaded.append(relative)
    return uploaded


def remove_temporary_boot_py(client: WebWorkflowClient) -> None:
    """Remove the temporary boot.py used to disable USB MSC during upload."""
    try:
        contents = client.download("boot.py")
    except HTTPError as exc:
        if exc.code == 404:
            exc.close()
            return
        raise

    if contents != TEMPORARY_BOOT_PY:
        raise RuntimeError(
            "boot.py does not match the expected temporary USB-mass-storage workaround; "
            "refusing to remove it"
        )

    try:
        with client.request("DELETE", "boot.py") as response:
            if response.status not in (200, 204):
                raise RuntimeError(f"temporary boot.py removal failed: HTTP {response.status}")
    except HTTPError as exc:
        if exc.code != 404:
            raise
        exc.close()

    try:
        client.download("boot.py")
    except HTTPError as exc:
        if exc.code == 404:
            exc.close()
            return
        raise
    raise RuntimeError("temporary boot.py still exists after removal")


def failure_messages(exc: BaseException) -> tuple[str, str]:
    """Return operator-safe diagnostics without reflecting credentials."""
    code = getattr(exc, "code", None)
    if code == 409:
        primary = (
            "Upload refused: CIRCUITPY is not writable. Eject the USB volume and retry; "
            "if HTTP 409 persists, follow the temporary boot.py USB-mass-storage "
            "workaround in hardware/matrixportal/README.md."
        )
    elif code in (401, 403):
        primary = "Upload refused: check the Web Workflow password and board address."
    elif isinstance(exc, KeyboardInterrupt):
        primary = "Upload interrupted before completion."
    elif isinstance(exc, URLError):
        primary = "Upload failed: could not reach the MatrixPortal Web Workflow endpoint."
    elif isinstance(exc, subprocess.CalledProcessError):
        primary = "Upload failed: application staging did not complete successfully."
    elif isinstance(exc, ValueError):
        primary = f"Upload failed: {exc}"
    elif isinstance(exc, OSError):
        primary = f"Upload failed: local file error ({exc.__class__.__name__})."
    else:
        primary = f"Upload failed: {exc}"
    recovery = "Leave the board paused and retry; use USB recovery if Wi-Fi is unavailable."
    return primary, recovery


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="http://matrixportal-s3.local", help="Board URL or http://host")
    parser.add_argument("--stage-dir", type=Path, default=DEFAULT_STAGE)
    parser.add_argument("--skip-stage", action="store_true", help="Use an existing staged directory")
    parser.add_argument(
        "--remove-temporary-boot-py",
        action="store_true",
        help="Remove and verify the temporary boot.py used to disable USB mass storage",
    )
    parser.add_argument(
        "--reload-and-capture-serial",
        type=int,
        metavar="SECONDS",
        help="send Ctrl-D and capture live serial output for the requested seconds",
    )
    parser.add_argument(
        "--capture-serial",
        type=int,
        metavar="SECONDS",
        help="capture live serial output without sending input",
    )
    args = parser.parse_args(argv)
    host = args.host if "://" in args.host else "http://" + args.host
    password = getpass.getpass("CircuitPython Web Workflow password: ")
    try:
        client = WebWorkflowClient(host, password)
        if args.capture_serial is not None:
            if args.capture_serial < 1 or args.capture_serial > 300:
                raise ValueError("serial capture duration must be between 1 and 300 seconds")
            serial = WebWorkflowSerial(host, password)
            try:
                print("Capturing board serial output without sending input.")
                for message in serial.read_text(args.capture_serial):
                    print(message, end="" if message.endswith("\n") else "\n")
            finally:
                serial.close()
            return 0
        if args.reload_and_capture_serial is not None:
            if args.reload_and_capture_serial < 1 or args.reload_and_capture_serial > 300:
                raise ValueError("serial capture duration must be between 1 and 300 seconds")
            serial = WebWorkflowSerial(host, password)
            try:
                serial.send_text(b"\x04")
                print("Reload requested; capturing board serial output.")
                for message in serial.read_text(args.reload_and_capture_serial):
                    print(message, end="" if message.endswith("\n") else "\n")
            finally:
                serial.close()
            return 0
        if args.remove_temporary_boot_py:
            remove_temporary_boot_py(client)
            print("Removed and verified temporary boot.py")
            print("Hard-reset the board to restore the default USB mass-storage interface.")
            return 0
        if not args.skip_stage:
            stage_application(args.stage_dir)
        names = upload(args.stage_dir, client)
    except (HTTPError, URLError, OSError, RuntimeError, ValueError, subprocess.CalledProcessError, KeyboardInterrupt) as exc:
        if isinstance(exc, HTTPError):
            exc.close()
        primary, recovery = failure_messages(exc)
        print(primary, file=sys.stderr)
        print(recovery, file=sys.stderr)
        return 1
    print(f"Uploaded and verified {len(names)} application files to {host}")
    print("Press Ctrl-D in the Web Workflow serial console to return to standard mode.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
