import contextlib
import importlib.util
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import HTTPError


SCRIPT = Path(__file__).parents[1] / "scripts" / "upload-firmware-wifi.py"
SPEC = importlib.util.spec_from_file_location("upload_firmware_wifi", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class FakeResponse:
    def __init__(self, status=200, body=b""):
        self.status = status
        self.body = body

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return self.body


class UploadFirmwareTests(unittest.TestCase):
    def test_staged_files_put_code_last(self):
        with tempfile.TemporaryDirectory() as directory:
            stage = Path(directory)
            (stage / "z.py").write_text("z")
            (stage / "code.py").write_text("code")
            (stage / "a.pem").write_text("pem")
            self.assertEqual([p.name for p in MODULE.staged_files(stage)], ["a.pem", "z.py", "code.py"])

    def test_upload_and_readback_hash(self):
        with tempfile.TemporaryDirectory() as directory:
            stage = Path(directory)
            (stage / "a.py").write_bytes(b"same")
            calls = []

            def opener(request, timeout):
                calls.append((request.method, request.full_url, request.data))
                if request.method == "PUT":
                    return FakeResponse(201)
                return FakeResponse(200, b"same")

            client = MODULE.WebWorkflowClient("http://board.local", "secret", opener)
            self.assertEqual(MODULE.upload(stage, client), ["a.py"])
            self.assertEqual([call[0] for call in calls], ["PUT", "GET"])
            self.assertNotIn("secret", calls[0][1])
            self.assertNotIn("secret", client.auth)

    def test_empty_stage_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                MODULE.staged_files(Path(directory))

    def test_auth_failure_is_safe_and_does_not_expose_password(self):
        password = "super-secret-password"
        error = HTTPError("http://board.local/fs/code.py", 401, "Unauthorized", None, None)
        stderr = io.StringIO()
        with (
            patch.object(MODULE.getpass, "getpass", return_value=password),
            patch.object(MODULE, "stage_application"),
            patch.object(MODULE, "upload", side_effect=error),
            contextlib.redirect_stderr(stderr),
        ):
            self.assertEqual(MODULE.main(["--host", "http://board.local"]), 1)
        output = stderr.getvalue()
        self.assertIn("check the Web Workflow password", output)
        self.assertIn("Leave the board paused and retry", output)
        self.assertNotIn(password, output)

    def test_usb_conflict_returns_eject_guidance(self):
        error = HTTPError("http://board.local/fs/code.py", 409, "Conflict", None, None)
        primary, recovery = MODULE.failure_messages(error)
        error.close()
        self.assertIn("CIRCUITPY is not writable", primary)
        self.assertIn("Eject the USB volume and retry", primary)
        self.assertIn("temporary boot.py USB-mass-storage workaround", primary)
        self.assertIn("Leave the board paused and retry", recovery)

    def test_remove_temporary_boot_py_deletes_and_verifies_file(self):
        calls = []

        class CleanupClient:
            def request(self, method, path):
                calls.append((method, path))
                return FakeResponse(204)

            def download(self, path):
                calls.append(("GET", path))
                raise HTTPError("http://board.local/fs/boot.py", 404, "Not Found", None, None)

        MODULE.remove_temporary_boot_py(CleanupClient())
        self.assertEqual(calls, [("DELETE", "boot.py"), ("GET", "boot.py")])

    def test_remove_temporary_boot_py_fails_if_file_remains(self):
        class CleanupClient:
            def request(self, method, path):
                return FakeResponse(204)

            def download(self, path):
                return b"import storage\\nstorage.disable_usb_drive()\\n"

        with self.assertRaisesRegex(RuntimeError, "still exists after removal"):
            MODULE.remove_temporary_boot_py(CleanupClient())

    def test_interrupted_upload_can_be_retried_from_start(self):
        with tempfile.TemporaryDirectory() as directory:
            stage = Path(directory)
            (stage / "a.py").write_bytes(b"a")
            (stage / "code.py").write_bytes(b"code")

            class RetryClient:
                def __init__(self):
                    self.fail_once = True
                    self.remote = {}
                    self.puts = []

                def upload(self, relative_path, data):
                    self.puts.append(relative_path)
                    if relative_path == "code.py" and self.fail_once:
                        self.fail_once = False
                        raise RuntimeError("simulated interruption")
                    self.remote[relative_path] = data

                def download(self, relative_path):
                    return self.remote[relative_path]

            client = RetryClient()
            with self.assertRaisesRegex(RuntimeError, "simulated interruption"):
                MODULE.upload(stage, client)

            self.assertEqual(MODULE.upload(stage, client), ["a.py", "code.py"])
            self.assertEqual(client.remote, {"a.py": b"a", "code.py": b"code"})
            self.assertEqual(client.puts, ["a.py", "code.py", "a.py", "code.py"])


if __name__ == "__main__":
    unittest.main()
