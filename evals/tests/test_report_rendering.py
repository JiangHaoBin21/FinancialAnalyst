from __future__ import annotations

import json
import unittest

from app.agents.report_agent import DEFAULT_DISCLAIMER, ReportAgent


class FakeLLMClient:
    def __init__(self, response: dict):
        self.response = response
        self.messages = None

    def generate(self, messages, **kwargs):
        self.messages = messages
        return json.dumps(self.response, ensure_ascii=False)


class ReportRenderingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.metric = {
            "name": "营业收入",
            "period": "2023-12-31",
            "value": 100.0,
            "unit": "亿元",
        }
        self.analysis = {
            "status": "analysis_done",
            "summary": "公司盈利表现稳定。",
            "overall_score": {
                "score": 82,
                "label": "良好",
                "basis": "基于盈利和现金流表现。",
                "confidence": "high",
            },
            "dimensions": [
                {
                    "name": "盈利能力",
                    "conclusion": "盈利表现稳定。",
                    "key_points": ["利润保持稳定"],
                    "supporting_metrics": [self.metric],
                }
            ],
            "data_limitations": ["缺少行业横向对比。"],
            "conclusion": "综合财务表现良好。",
        }

    def _state(self) -> dict:
        return {
            "user_query": "请分析示例公司。",
            "analysis_focus": "盈利能力",
            "company_profile": {"company_name": "示例公司"},
            "time_range": {"start_year": 2023, "end_year": 2023},
            "analysis_result": self.analysis,
            "trans_message": "分析阶段通过。",
        }

    def test_code_inherits_protected_fields_and_renders_markdown(self) -> None:
        fake = FakeLLMClient(
            {
                "status": "report_failed",
                "report_type": "financial_analysis",
                "title": "示例公司财务分析报告",
                "executive_summary": "盈利总体稳定。",
                "overall_assessment": {"score": 1},
                "sections": [
                    {
                        "heading": "盈利能力",
                        "summary": "盈利表现稳定。",
                        "key_points": ["利润保持稳定"],
                        "supporting_metrics": [
                            {"name": "伪造指标", "period": "2023", "value": 999}
                        ],
                    }
                ],
                "risk_warnings": ["仍需关注外部经营环境变化。"],
                "data_limitations": ["被模型改写的限制"],
                "conclusion": "综合表现良好。",
                "disclaimer": "可以买入。",
                "markdown_report": "# 模型伪造的 Markdown",
            }
        )
        result = ReportAgent(fake).run(self._state())

        self.assertEqual(result["status"], "report_ready")
        self.assertEqual(result["overall_assessment"], self.analysis["overall_score"])
        self.assertEqual(result["sections"][0]["supporting_metrics"], [self.metric])
        self.assertEqual(result["data_limitations"], ["缺少行业横向对比。"])
        self.assertEqual(result["disclaimer"], DEFAULT_DISCLAIMER)
        self.assertNotIn("模型伪造的 Markdown", result["markdown_report"])
        self.assertIn("# 示例公司财务分析报告", result["markdown_report"])
        self.assertIn("## 五、数据限制", result["markdown_report"])
        self.assertIn("缺少行业横向对比。", result["markdown_report"])
        self.assertIn("营业收入", result["markdown_report"])
        self.assertIn("## 七、免责声明", result["markdown_report"])
        self.assertIn("不构成任何投资建议", result["markdown_report"])

    def test_missing_generated_section_falls_back_to_analysis(self) -> None:
        fake = FakeLLMClient(
            {
                "report_type": "unknown_type",
                "title": "",
                "executive_summary": "",
                "sections": [],
                "risk_warnings": [],
                "conclusion": "",
            }
        )
        result = ReportAgent(fake).run(self._state())

        self.assertEqual(result["report_type"], "general_report")
        self.assertEqual(result["executive_summary"], self.analysis["summary"])
        self.assertEqual(result["sections"][0]["heading"], "盈利能力")
        self.assertEqual(result["sections"][0]["summary"], "盈利表现稳定。")
        self.assertEqual(result["conclusion"], self.analysis["conclusion"])

    def test_prompt_explicitly_excludes_markdown(self) -> None:
        fake = FakeLLMClient(
            {
                "report_type": "financial_analysis",
                "title": "报告",
                "executive_summary": "摘要",
                "sections": [],
                "risk_warnings": [],
                "conclusion": "结论",
            }
        )
        ReportAgent(fake).run(self._state())
        system_prompt = fake.messages[0]["content"]
        self.assertIn("不要输出 status", system_prompt)
        self.assertIn("markdown_report", system_prompt)
        self.assertIn("完整 Markdown 由程序", system_prompt)

    def test_malformed_generated_collections_fall_back_to_valid_lists(self) -> None:
        fake = FakeLLMClient(
            {
                "report_type": "financial_analysis",
                "title": "报告",
                "executive_summary": "摘要",
                "sections": [
                    {
                        "heading": "被模型改写的标题",
                        "summary": "报告化小结",
                        "key_points": "错误的字符串",
                    }
                ],
                "risk_warnings": "错误的字符串",
                "conclusion": "结论",
            }
        )
        result = ReportAgent(fake).run(self._state())

        self.assertEqual(result["sections"][0]["heading"], "盈利能力")
        self.assertEqual(result["sections"][0]["key_points"], ["利润保持稳定"])
        self.assertEqual(result["risk_warnings"], [])


if __name__ == "__main__":
    unittest.main()
