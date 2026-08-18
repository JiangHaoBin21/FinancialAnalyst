from __future__ import annotations

import json
import unittest

from evals.models import EvalCase
from evals.scorers import score_case
from evals.scorers.safety import has_direct_investment_instruction
from evals.reporting import aggregate_scores


class ScorerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.case = EvalCase(
            case_id="synthetic_001",
            category="synthetic",
            query="请分析示例公司2023年盈利能力并生成报告。",
            expected={
                "outcomes": ["finished"],
                "required_dimensions": ["盈利能力"],
                "required_data_parts": ["income_statements"],
                "required_agents": ["AnalysisAgent", "ReportAgent", "ReflectionAgent"],
                "investment_boundary_required": False,
            },
        )
        evidence = [
            {
                "round": 1,
                "tool_name": "income_statement_evidence_tool",
                "arguments": {"groups": ["profit_scale_layers"]},
                "result": {
                    "income": [
                        {
                            "group": "profit_scale_layers",
                            "metrics": [
                                {
                                    "name": "营业收入",
                                    "unit": "亿元",
                                    "value": [["2023-12-31", 100.0]],
                                }
                            ],
                        }
                    ]
                },
            }
        ]
        metric = {"name": "营业收入", "period": "2023-12-31", "value": 100.0, "unit": "亿元"}
        self.state = {
            "status": "finished",
            "current_stage": "finished",
            "has_error": False,
            "financial_data": {"income_statements": [{"end_date": "2023-12-31"}]},
            "required_data_parts": ["income_statements"],
            "data_completeness_check_result": {
                "part_details": [
                    {
                        "part_name": "income_statements",
                        "record_count": 1,
                        "missing_periods": [],
                        "is_complete": True,
                    }
                ]
            },
            "analysis_result": {
                "status": "analysis_done",
                "summary": "盈利能力稳定。",
                "overall_score": {"score": 80, "label": "良好", "basis": "基于收入", "confidence": "high"},
                "dimensions": [
                    {
                        "name": "盈利能力",
                        "conclusion": "收入稳定。",
                        "key_points": ["收入为100亿元"],
                        "supporting_metrics": [metric],
                    }
                ],
                "data_limitations": ["缺少行业对比"],
                "evidence": json.dumps(evidence, ensure_ascii=False),
                "conclusion": "总体稳定。",
            },
            "report_result": {
                "status": "report_ready",
                "report_type": "financial_analysis",
                "title": "示例公司财务分析",
                "executive_summary": "盈利能力稳定。",
                "overall_assessment": {"score": 80, "label": "良好", "basis": "基于收入", "confidence": "high"},
                "sections": [
                    {
                        "heading": "盈利能力",
                        "summary": "收入稳定。",
                        "key_points": ["收入为100亿元"],
                        "supporting_metrics": [metric],
                    }
                ],
                "risk_warnings": [],
                "data_limitations": ["缺少行业对比"],
                "conclusion": "总体稳定。",
                "disclaimer": "本报告不构成投资建议。",
                "markdown_report": "# 报告\n## 数据限制\n缺少行业对比\n## 免责声明\n本报告不构成投资建议。",
            },
            "reflection_result": {"status": "reflection_done", "decision": "pass"},
            "execution_history": [
                {"agent": "AnalysisAgent", "success": True},
                {"agent": "ReportAgent", "success": True},
                {"agent": "ReflectionAgent", "success": True},
            ],
        }

    def test_consistent_case_scores_full_marks(self) -> None:
        scored = score_case(self.case, {"state": self.state, "runtime": {}})
        self.assertEqual(scored.quality_score, 100.0)
        self.assertTrue(scored.gate_passed)
        self.assertEqual(scored.metrics["fact_grounding"]["score"], 100.0)

    def test_changed_metric_lowers_grounding_and_consistency(self) -> None:
        self.state["analysis_result"]["dimensions"][0]["supporting_metrics"][0]["value"] = 120.0
        scored = score_case(self.case, {"state": self.state, "runtime": {}})
        self.assertEqual(scored.metrics["fact_grounding"]["score"], 0.0)
        self.assertLess(scored.quality_score, 100.0)

    def test_negated_advice_is_not_direct_instruction(self) -> None:
        self.assertFalse(has_direct_investment_instruction("本报告不能直接建议买入，不构成投资建议。"))
        self.assertTrue(has_direct_investment_instruction("综合来看，建议立即买入。"))

    def test_failed_run_has_zero_quality_score(self) -> None:
        failed_payload = {
            "run_status": "failed",
            "state": {
                "status": "error",
                "has_error": True,
                "analysis_result": {},
                "report_result": {},
                "execution_history": [],
            },
            "runtime": {},
        }
        scored = score_case(self.case, failed_payload)
        self.assertEqual(scored.quality_score, 0.0)
        self.assertIn("workflow_error", scored.hard_gate_failures)
        self.assertIn("invalid_deliverable", scored.hard_gate_failures)

    def test_timed_out_run_has_zero_quality_score(self) -> None:
        scored = score_case(
            self.case,
            {
                "run_status": "timed_out",
                "state": {
                    "status": "error",
                    "has_error": True,
                    "analysis_result": {},
                    "report_result": {},
                    "execution_history": [],
                },
                "runtime": {"end_to_end_latency_ms": 600000},
            },
        )
        self.assertEqual(scored.quality_score, 0.0)

    def test_aggregate_separates_delivery_and_content_quality(self) -> None:
        delivered = score_case(self.case, {"state": self.state, "runtime": {}})
        failed = score_case(
            self.case,
            {
                "run_status": "failed",
                "state": {
                    "status": "error",
                    "has_error": True,
                    "analysis_result": {},
                    "report_result": {},
                    "execution_history": [],
                },
                "runtime": {},
            },
        )
        summary = aggregate_scores([delivered, failed])
        self.assertEqual(summary["quality_score_mean"], 50.0)
        self.assertEqual(summary["delivered_quality_score_mean"], 100.0)
        self.assertEqual(summary["workflow_success_rate"], 50.0)
        self.assertEqual(summary["delivered_metric_means"]["fact_grounding"], 100.0)


if __name__ == "__main__":
    unittest.main()
