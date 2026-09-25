import importlib.util
from pathlib import Path
import tempfile
import unittest


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


if __name__ == "__main__":
    unittest.main()
