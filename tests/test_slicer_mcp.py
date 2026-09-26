from __future__ import annotations

import asyncio
import json
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

from mcp_servers.slicer import server
from mcp_servers.slicer.service import (
    ROOT,
    BambuStudioProvider,
    SlicerService,
    SlicerServiceError,
)


TEST_MODEL = (
    ROOT
    / "hardware/enclosure/direct-mount/stl"
    / "09_centre_boss_desk_stand_PRINT_3.stl"
)


class SlicerServiceTests(unittest.TestCase):
    def setUp(self):
        self.provider = BambuStudioProvider(timeout_seconds=5)
        self.service = SlicerService(self.provider)

    def test_capabilities_keep_cloudflare_endpoint_separate(self):
        payload = self.service.capabilities()

        self.assertEqual(payload["service"], "led-slicer-mcp")
        self.assertFalse(
            payload["cloudflare_remote_endpoint"]["configured"]
        )
        self.assertEqual(
            payload["cloudflare_remote_endpoint"]["recommended_path_if_deployed"],
            "/mcp/slicer",
        )

    def test_rejects_path_outside_allowlist(self):
        with self.assertRaises(SlicerServiceError):
            self.provider.inspect_model("/etc/passwd")

    def test_inspects_tracked_stl(self):
        payload = self.provider.inspect_model(str(TEST_MODEL.relative_to(ROOT)))

        self.assertGreater(payload["size_bytes"], 0)
        self.assertGreater(payload["vertices"], 0)
        self.assertGreater(payload["faces"], 0)
        self.assertEqual(payload["suffix"], ".stl")
        self.assertEqual(len(payload["dimensions_mm"]), 3)

    def test_slice_uses_shared_script_and_returns_structured_result(self):
        def fake_run(command, **kwargs):
            output_dir = Path(command[-1])
            artifact = output_dir / f"{TEST_MODEL.stem}.sliced.3mf"
            artifact.write_bytes(b"test-3mf")
            (output_dir / "slicer.log").write_text("clean slice\n", encoding="utf-8")
            (output_dir / "result.json").write_text(
                json.dumps(
                    {
                        "ok": True,
                        "categories": [],
                        "fatal_categories": [],
                        "slicer_exit": 0,
                        "artifact": str(artifact),
                        "slice_seconds": 0.42,
                    }
                ),
                encoding="utf-8",
            )
            return subprocess.CompletedProcess(command, 0, "", "")

        with patch(
            "mcp_servers.slicer.service.subprocess.run",
            side_effect=fake_run,
        ) as mocked:
            payload = self.provider.slice(
                str(TEST_MODEL.relative_to(ROOT)),
                orient=False,
            )

        self.assertTrue(payload["ok"])
        self.assertEqual(payload["provider"], "bambustudio")
        self.assertFalse(payload["orient"])
        command = mocked.call_args.args[0]
        self.assertEqual(command[0], "bash")
        self.assertTrue(command[1].endswith("scripts/slicer/slice-stl.sh"))
        env = mocked.call_args.kwargs["env"]
        self.assertEqual(env["SLICER_ORIENT"], "0")
        self.assertEqual(env["SLICER_MACHINE_PROFILE"], "Bambu Lab H2D 0.4 nozzle")

    def test_prepare_print_never_marks_print_started(self):
        with patch.object(
            self.provider,
            "slice",
            return_value={
                "ok": True,
                "artifact": "artifacts/slicer/test/part.sliced.3mf",
                "categories": [],
            },
        ):
            payload = self.service.prepare_print(
                path_value=str(TEST_MODEL.relative_to(ROOT))
            )

        self.assertTrue(payload["ready_for_print"])
        self.assertFalse(payload["print_started"])
        self.assertFalse(payload["printer_handoff_available"])

    def test_timeout_is_a_safe_error(self):
        with patch(
            "mcp_servers.slicer.service.subprocess.run",
            side_effect=subprocess.TimeoutExpired(["bash"], 5),
        ):
            with self.assertRaisesRegex(SlicerServiceError, "exceeded timeout"):
                self.provider.slice(str(TEST_MODEL.relative_to(ROOT)))


class SlicerMcpContractTests(unittest.IsolatedAsyncioTestCase):
    async def test_expected_tools_are_registered(self):
        tools = await server.mcp.list_tools()
        names = {tool.name for tool in tools}

        self.assertEqual(
            names,
            {
                "slicer_capabilities",
                "slicer_inspect_model",
                "slicer_list_profiles",
                "slicer_slice",
                "slicer_validate_for_print",
                "slicer_prepare_print",
            },
        )


if __name__ == "__main__":
    unittest.main()
