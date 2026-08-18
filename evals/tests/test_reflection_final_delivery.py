from __future__ import annotations

import unittest
from unittest.mock import patch

from app.application.financial_analysis_runner import FinancialAnalysisResult
from app.workflows.nodes import WorkflowNodes
from app.workflows.state import create_initial_state, plan_step


class FakeAgent:
    def __init__(self, result: dict):
        self.result = result

    def run(self, state: dict) -> dict:
        return dict(self.result)


class ReflectionFinalDeliveryTests(unittest.TestCase):
    @staticmethod
    def _state_for(agent_name: str) -> dict:
        state = create_initial_state("请分析示例公司")
        state.update(
            {
                "task_plan": [
                    plan_step(
                        step_id=1,
                        agent=agent_name,
                        action="test",
                        description="test",
                    )
                ],
                "current_step_index": 0,
                "report_result": {"markdown_report": "# Report 原稿"},
            }
        )
        return state

    def test_minor_revision_becomes_final_delivery(self) -> None:
        revised = "# Reflection 修订稿\n\n措辞已修正。"
        reflection = FakeAgent(
            {
                "status": "reflection_done",
                "decision": "pass_with_minor_revision",
                "recommended_next_stage": "finished",
                "final_report_markdown": revised,
            }
        )
        nodes = WorkflowNodes(supervisor_agent=None, reflection_agent=reflection)
        state = self._state_for("ReflectionAgent")

        reflection_update = nodes.reflection_node(state)
        self.assertEqual(reflection_update["final_report"], revised)

        finished_state = {**state, **reflection_update}
        finish_update = nodes.finish_node(finished_state)
        self.assertEqual(finish_update["final_report"], revised)
        self.assertEqual(finish_update["final_response"], revised)

        result = FinancialAnalysisResult.from_state(
            {**finished_state, **finish_update}
        )
        self.assertEqual(result.final_report, revised)

    def test_pass_promotes_report_draft_to_final_delivery(self) -> None:
        reflection = FakeAgent(
            {
                "status": "reflection_done",
                "decision": "pass",
                "recommended_next_stage": "finished",
                "final_report_markdown": None,
            }
        )
        nodes = WorkflowNodes(supervisor_agent=None, reflection_agent=reflection)

        update = nodes.reflection_node(self._state_for("ReflectionAgent"))

        self.assertEqual(update["final_report"], "# Report 原稿")

    def test_regeneration_decision_invalidates_stale_final_report(self) -> None:
        reflection = FakeAgent(
            {
                "status": "reflection_done",
                "decision": "needs_report_regeneration",
                "recommended_next_stage": "report",
                "final_report_markdown": None,
            }
        )
        nodes = WorkflowNodes(supervisor_agent=None, reflection_agent=reflection)
        state = self._state_for("ReflectionAgent")
        state["final_report"] = "# 上一轮修订稿"

        update = nodes.reflection_node(state)

        self.assertIsNone(update["final_report"])
        finished = nodes.finish_node({**state, **update})
        self.assertIsNone(finished["final_report"])

    def test_missing_minor_revision_does_not_fall_back_to_original(self) -> None:
        reflection = FakeAgent(
            {
                "status": "reflection_done",
                "decision": "pass_with_minor_revision",
                "recommended_next_stage": "finished",
                "final_report_markdown": None,
            }
        )
        nodes = WorkflowNodes(supervisor_agent=None, reflection_agent=reflection)
        state = self._state_for("ReflectionAgent")

        update = nodes.reflection_node(state)
        finished = nodes.finish_node({**state, **update})

        self.assertIsNone(update["final_report"])
        self.assertIsNone(finished["final_report"])

    def test_new_report_invalidates_previous_delivery(self) -> None:
        report = FakeAgent(
            {
                "status": "report_ready",
                "markdown_report": "# 新报告草稿",
            }
        )
        nodes = WorkflowNodes(supervisor_agent=None, report_agent=report)
        state = self._state_for("ReportAgent")
        state["final_report"] = "# 上一轮修订稿"
        state["final_response"] = "# 上一轮修订稿"
        state["reflection_result"] = {
            "decision": "pass_with_minor_revision",
            "final_report_markdown": "# 上一轮修订稿",
        }

        with patch("app.workflows.nodes.save_markdown_report"):
            update = nodes.report_node(state)

        self.assertIsNone(update["final_report"])
        self.assertIsNone(update["final_response"])
        self.assertEqual(update["reflection_result"], {})
        self.assertEqual(update["report_result"]["markdown_report"], "# 新报告草稿")
        self.assertEqual(
            FinancialAnalysisResult.from_state({**state, **update}).final_report,
            "# 新报告草稿",
        )

    def test_legacy_state_reads_revision_nested_in_reflection_result(self) -> None:
        revised = "# 旧 checkpoint 中的 Reflection 修订稿"
        state = self._state_for("ReflectionAgent")
        state["reflection_result"] = {
            "decision": "pass_with_minor_revision",
            "final_report_markdown": revised,
        }

        result = FinancialAnalysisResult.from_state(state)

        self.assertEqual(result.final_report, revised)


if __name__ == "__main__":
    unittest.main()
