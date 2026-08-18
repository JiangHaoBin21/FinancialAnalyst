"""ReportAgent: minimal report generation implementation."""

from __future__ import annotations

from typing import Any

from app.skills.supervisor.planning_parser import parse_json_response
from app.utils.markdown_report_renderer import render_markdown_report
from app.workflows.state import WorkflowState


DEFAULT_DISCLAIMER = (
    "本报告仅基于已获取的公开财务数据和模型分析结果生成，"
    "仅供财务研究参考，不构成任何投资建议。"
)

VALID_REPORT_TYPES = {
    "financial_analysis",
    "investment_reference",
    "risk_analysis",
    "general_report",
}


class ReportAgent:
    def __init__(self, llm_client):
        self.llm_client = llm_client

    def run(self, state: WorkflowState) -> dict:
        analysis_result_for_report = self._build_analysis_for_report(state.get("analysis_result"))
        messages = self._build_messages(
            user_query=state.get("user_query"),
            analysis_focus=state.get("analysis_focus"),
            company_profile=state.get("company_profile"),
            time_range=state.get("time_range"),
            analysis_for_report=analysis_result_for_report,
            trans_message=state.get("trans_message"),
        )
        report_result = self.llm_client.generate(messages=messages)
        if not report_result:
            raise ValueError("report大模型返回空结果。")
        parsed_results = parse_json_response(report_result)
        if not parsed_results:
            raise ValueError("解析report大模型返回结果失败。")
        normalized_result = self._normalize_report_result(
            result=parsed_results,
            analysis_result=analysis_result_for_report,
        )
        normalized_result["markdown_report"] = render_markdown_report(normalized_result)
        return normalized_result

    def _build_analysis_for_report(self, analysis_result: dict[str, Any] | None) -> dict[str, Any]:
        if analysis_result is None:
            raise ValueError("从state中获取到的analysis_result为空")
        return {
            "status": analysis_result.get("status"),
            "summary": analysis_result.get("summary"),
            "overall_score": analysis_result.get("overall_score"),
            "dimensions": analysis_result.get("dimensions", []),
            "data_limitations": analysis_result.get("data_limitations", []),
            "conclusion": analysis_result.get("conclusion"),
        }

    def _build_messages(
            self,
            *,
            user_query: str | None,
            analysis_focus: str | None,
            company_profile: dict | None,
            time_range: dict | None,
            analysis_for_report: dict | None,
            trans_message: str | None,
    ):
        system_prompt = """
你是一个专业的财务分析报告生成 Agent，负责基于 AnalysisAgent 已经完成的结构化分析结果，生成一份正式、清晰、克制、可展示的财务分析报告。

你的核心职责：
1. 基于输入中的 AnalysisAgent 结果生成报告；
2. 负责报告结构组织、语言润色、章节编排、摘要提炼和风险提示；
3. 将结构化分析结果转换为用户可阅读的正式报告；
4. 面向 user_query 和 analysis_focus 调整报告重点；
5. 只输出精简的结构化 report_result；完整 Markdown 由程序根据结构化字段渲染。

你的职责边界：
1. 你不是财务分析 Agent，不能重新进行财务分析；
2. 你不能重新计算任何财务指标；
3. 你不能重新打分；
4. 你不能编造输入中不存在的财务数据、指标、同比、环比、行业排名、估值、股价走势、市占率或预测信息；
5. 你不能推翻 AnalysisAgent 已经给出的核心判断；
6. 你不能绕过 AnalysisAgent 的结论，基于原始 evidence 重新分析；
7. 如果输入中存在 data_limitations，程序会原样继承，你不得改写；
8. 如果用户问题涉及股票买卖、投资价值、是否值得买入、能不能买等内容，只能从财务基本面角度说明，不得给出买入、卖出、持有等直接投资建议。

字段映射规则：
1. report_type：
   - 如果用户问题是常规财务表现分析，输出 financial_analysis；
   - 如果用户问题涉及股票能不能买、是否值得投资、投资价值，输出 investment_reference；
   - 如果用户问题主要询问风险，输出 risk_analysis；
   - 其他情况输出 general_report。

2. sections：
   - 必须由输入中的 dimensions 转换而来；
   - 程序会使用 dimension.name 作为最终 section.heading；
   - dimension.conclusion 对应 section.summary；
   - dimension.key_points 对应 section.key_points；
   - 可以对 summary、key_points 进行轻微报告化润色；
   - 不得删除核心结论；
   - 不得新增没有依据的指标和事实。

3. supporting_metrics：
   - 不需要输出 supporting_metrics；程序会按章节顺序从 dimensions 原样继承；
   - 你只负责 section 的 heading、summary 和 key_points。

4. risk_warnings：
   - 可以从 dimensions、data_limitations 和用户问题中提炼；
   - 风险提示必须克制、准确；
   - 可以使用“需要关注”“仍需观察”“存在不确定性”等表达；
   - 不得将“风险可控”改写为“风险较大”；
   - 不得夸大为“严重危机”“明显恶化”“高风险”，除非输入中明确这样判断；
   - 投资类问题必须包含“未覆盖估值、股价走势、行业景气度、市场情绪、个人风险偏好”等边界提示。

5. conclusion：
   - 必须基于 AnalysisAgent 的 summary、overall_score 和 conclusion 生成；
   - 可以压缩和报告化表达；
   - 不得新增未提供的事实；
   - 投资类问题不得输出直接买入、卖出或持有建议。

一致性要求：
1. executive_summary、sections、risk_warnings 和 conclusion 必须相互一致；
2. 如果 data_limitations 指出缺少同比或行业对比数据，则不得强调同比增长、行业领先等缺乏依据的表述；
3. 如果输入中存在内部表述冲突，应优先遵守 data_limitations，并使用更谨慎的表达；
4. 报告语言应专业、清晰、克制，避免营销化、绝对化、预测性表达。

输出要求：
1. 只输出严格 JSON；
2. 不要输出解释性文字；
3. 不要输出 status、overall_assessment、supporting_metrics、data_limitations、disclaimer 或 markdown_report；这些字段全部由程序确定性生成。
4. JSON 必须包含以下完整字段：

{
  "report_type": "financial_analysis | investment_reference | risk_analysis | general_report",
  "title": "报告标题",
  "executive_summary": "报告核心摘要",
  "sections": [
    {
      "heading": "章节标题",
      "summary": "章节小结",
      "key_points": ["要点1", "要点2"]
    }
  ],
  "risk_warnings": ["风险提示1", "风险提示2"],
  "conclusion": "综合结论"
}
        """
        user_prompt = f"""
用户原始问题 user_query：
{user_query}

分析重点 analysis_focus：
{analysis_focus}

公司信息：
{company_profile}

分析时间范围：
{time_range}

AnalysisAgent 结构化分析结果：
{analysis_for_report}

SupervisorAgent 对于 AnalysisAgent 分析结果的审查结果：
{trans_message}

请基于以上信息生成 report_result。

生成要求：
1. 只基于 AnalysisAgent 结构化分析结果生成报告；
2. 不使用未提供的数据；
3. 不新增财务指标；
4. 不重新计算指标；
5. 不重新打分；
6. sections 必须与 dimensions 数量和顺序一致；
7. 不要输出 status、supporting_metrics、overall_assessment、data_limitations、disclaimer 或 markdown_report；
8. 输出必须是严格 JSON，不要输出任何 JSON 以外的内容。
"""
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

    def _normalize_report_result(
            self,
            result: dict[str, Any],
            analysis_result: dict[str, Any],
    ) -> dict[str, Any]:
        overall_score = analysis_result.get("overall_score") or {}

        sections = self._normalize_sections(
            generated_sections=result.get("sections"),
            dimensions=analysis_result.get("dimensions") or [],
        )

        return {
            "status": self._report_status(analysis_result.get("status")),
            "report_type": self._report_type(result.get("report_type")),
            "title": self._text(result.get("title"), "财务分析报告"),
            "executive_summary": self._text(
                result.get("executive_summary"),
                self._text(analysis_result.get("summary")),
            ),
            "overall_assessment": {
                "score": overall_score.get("score"),
                "label": overall_score.get("label", ""),
                "basis": overall_score.get("basis", ""),
                "confidence": overall_score.get("confidence", "medium"),
            },
            "sections": sections,
            "risk_warnings": self._text_list(result.get("risk_warnings")),
            "data_limitations": list(analysis_result.get("data_limitations") or []),
            "conclusion": self._text(
                result.get("conclusion"),
                self._text(analysis_result.get("conclusion")),
            ),
            "disclaimer": DEFAULT_DISCLAIMER,
            "markdown_report": "",
        }

    @staticmethod
    def _normalize_sections(
        *,
        generated_sections: Any,
        dimensions: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        generated = generated_sections if isinstance(generated_sections, list) else []
        sections: list[dict[str, Any]] = []
        for index, dimension in enumerate(dimensions):
            section = generated[index] if index < len(generated) and isinstance(generated[index], dict) else {}
            sections.append(
                {
                    "heading": ReportAgent._text(
                        dimension.get("name"),
                        f"分析维度 {index + 1}",
                    ),
                    "summary": ReportAgent._text(
                        section.get("summary"),
                        ReportAgent._text(dimension.get("conclusion")),
                    ),
                    "key_points": (
                        ReportAgent._text_list(section.get("key_points"))
                        or ReportAgent._text_list(dimension.get("key_points"))
                    ),
                    "supporting_metrics": list(dimension.get("supporting_metrics") or []),
                }
            )
        return sections

    @staticmethod
    def _report_status(analysis_status: Any) -> str:
        return {
            "analysis_done": "report_ready",
            "analysis_partial": "report_partial",
            "needs_more_data": "report_partial",
            "analysis_failed": "report_failed",
        }.get(str(analysis_status or ""), "report_partial")

    @staticmethod
    def _report_type(value: Any) -> str:
        normalized = str(value or "")
        return normalized if normalized in VALID_REPORT_TYPES else "general_report"

    @staticmethod
    def _text(value: Any, default: str = "") -> str:
        text = str(value or "").strip()
        return text or default

    @staticmethod
    def _text_list(value: Any) -> list[str]:
        if not isinstance(value, list):
            return []
        return [
            text
            for item in value
            if (text := str(item or "").strip())
        ]

