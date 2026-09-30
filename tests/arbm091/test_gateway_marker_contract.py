import argparse
from contextlib import ExitStack
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from arbm091 import gateway_supervisor as supervisor


class GatewayMarkerContractTests(unittest.TestCase):
    def _run(self, root, marker, evidence="", child_rc=0):
        ledger=Path(root)/"shim.jsonl"
        ledger.write_text(evidence)
        args=argparse.Namespace(artifact_dir=root, shim_log=str(Path(root)/"shim.log"),
            telemetry_log=str(Path(root)/"telemetry.jsonl"),
            run_log=str(Path(root)/"run.log"), marker=marker,
            marker_file=str(ledger),run_cmd="unused",run_cwd=None,timeout=10)
        shim=mock.Mock(pid=123)
        shim.poll.return_value=None
        child=mock.Mock(pid=456)
        child.poll.return_value=child_rc
        with ExitStack() as stack:
            stack.enter_context(mock.patch.object(supervisor,"start_shim",return_value=(shim,mock.Mock())))
            stack.enter_context(mock.patch.object(supervisor,"wait_ready"))
            stack.enter_context(mock.patch.object(supervisor,"health",return_value=True))
            stack.enter_context(mock.patch.object(supervisor,"snapshot"))
            stack.enter_context(mock.patch.object(supervisor,"stop_process"))
            stack.enter_context(mock.patch.object(supervisor.subprocess,"Popen",return_value=child))
            return supervisor.run_supervised(args)

    def test_zero_exit_without_requested_marker_is_not_proof(self):
        with tempfile.TemporaryDirectory() as root:
            with self.assertRaisesRegex(RuntimeError,"SUPERVISED_MARKER_NOT_PROVEN"):
                self._run(root,"TASK091_MICRO_SUMMARYARR_PROVEN",
                    '{"status":"TERMINAL_FAIL","reason":"TASK091_FIXED_WIDTH_START_CARET_UNPROVEN"}\n')

    def test_requested_marker_remains_success(self):
        with tempfile.TemporaryDirectory() as root:
            self.assertEqual(self._run(root,"TASK091_MICRO_SECTION_E_PROVEN",
                '{"status":"TERMINAL_FAIL","reason":"TASK091_MICRO_SECTION_E_PROVEN"}\n'),0)

    def test_full_run_without_marker_keeps_exit_contract(self):
        with tempfile.TemporaryDirectory() as root:
            self.assertEqual(self._run(root,""),0)
        with tempfile.TemporaryDirectory() as root:
            self.assertEqual(self._run(root,"",child_rc=7),7)
