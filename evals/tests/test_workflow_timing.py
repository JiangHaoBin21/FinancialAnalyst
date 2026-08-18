from __future__ import annotations

import io
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from app.workflows.graph import WorkflowGraph


class WorkflowTimingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.graph = object.__new__(WorkflowGraph)
        self.graph.enable_trace = False

    def test_successful_stage_prints_elapsed_time(self) -> None:
        def analysis_node(state):
            return {"status": "analysis_ready", "current_stage": "analysis"}

        wrapped = self.graph._wrap_node(analysis_node)
        output = io.StringIO()
        with patch("app.workflows.graph.perf_counter", side_effect=[10.0, 11.23456]):
            with redirect_stdout(output):
                result = wrapped({"has_error": False})

        self.assertEqual(result["status"], "analysis_ready")
        self.assertIn("[阶段耗时] Analysis 完成，耗时 1.235 秒", output.getvalue())

    def test_error_update_prints_failed_status(self) -> None:
        def report_node(state):
            return {"status": "error", "current_stage": "error", "has_error": True}

        wrapped = self.graph._wrap_node(report_node)
        output = io.StringIO()
        with patch("app.workflows.graph.perf_counter", side_effect=[20.0, 20.5]):
            with redirect_stdout(output):
                wrapped({"has_error": False})

        self.assertIn("[阶段耗时] Report 失败，耗时 0.500 秒", output.getvalue())

    def test_exception_prints_timing_before_reraising(self) -> None:
        def reflection_node(state):
            raise RuntimeError("boom")

        wrapped = self.graph._wrap_node(reflection_node)
        output = io.StringIO()
        with patch("app.workflows.graph.perf_counter", side_effect=[30.0, 30.25]):
            with redirect_stdout(output):
                with self.assertRaisesRegex(RuntimeError, "boom"):
                    wrapped({})

        self.assertIn("[阶段耗时] Reflection 失败，耗时 0.250 秒", output.getvalue())


if __name__ == "__main__":
    unittest.main()
