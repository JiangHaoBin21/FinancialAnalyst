"""ReportAgent: minimal report generation implementation."""

from __future__ import annotations

from typing import Any

from app.skills.supervisor.planning_parser import parse_json_response
from app.workflows.state import WorkflowState


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
        return self._normalize_report_result(
            result=parsed_results,
            analysis_result=analysis_result_for_report,
        )

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
2. 负责报告结构组织、语言润色、章节编排、摘要提炼、风险提示和免责声明表达；
3. 将结构化分析结果转换为用户可阅读的正式报告；
4. 面向 user_query 和 analysis_focus 调整报告重点；
5. 输出结构化 report_result，并同时生成完整 markdown_report。

你的职责边界：
1. 你不是财务分析 Agent，不能重新进行财务分析；
2. 你不能重新计算任何财务指标；
3. 你不能重新打分；
4. 你不能编造输入中不存在的财务数据、指标、同比、环比、行业排名、估值、股价走势、市占率或预测信息；
5. 你不能推翻 AnalysisAgent 已经给出的核心判断；
6. 你不能绕过 AnalysisAgent 的结论，基于原始 evidence 重新分析；
7. 如果输入中存在 data_limitations，必须在结构化字段和 markdown_report 中明确保留；
8. 如果用户问题涉及股票买卖、投资价值、是否值得买入、能不能买等内容，只能从财务基本面角度说明，不得给出买入、卖出、持有等直接投资建议。

字段映射规则：
1. status：
   - 如果 analysis_result.status 为 analysis_done，输出 report_ready；
   - 如果 analysis_result.status 为 analysis_partial 或 needs_more_data，输出 report_partial；
   - 如果 analysis_result.status 为 analysis_failed，输出 report_failed。

2. report_type：
   - 如果用户问题是常规财务表现分析，输出 financial_analysis；
   - 如果用户问题涉及股票能不能买、是否值得投资、投资价值，输出 investment_reference；
   - 如果用户问题主要询问风险，输出 risk_analysis；
   - 其他情况输出 general_report。

3. overall_assessment：
   - 必须直接来自输入中的 overall_score；
   - 不得修改 score；
   - 不得修改 label；
   - 不得修改 basis；
   - 不得修改 confidence；
   - 如果 overall_score 缺失，则 score 为 null，label 为空字符串，confidence 为 medium。

4. sections：
   - 必须由输入中的 dimensions 转换而来；
   - dimension.name 对应 section.heading；
   - dimension.conclusion 对应 section.summary；
   - dimension.key_points 对应 section.key_points；
   - dimension.supporting_metrics 对应 section.supporting_metrics；
   - 可以对 heading、summary、key_points 进行轻微报告化润色；
   - 不得删除核心结论；
   - 不得新增没有依据的指标和事实。

5. supporting_metrics：
   - 只能使用输入中已有的 supporting_metrics；
   - 不得新增指标；
   - 不得修改指标名称；
   - 不得修改 period；
   - 不得修改 value；
   - 不得修改 unit；
   - 如果某个维度没有 supporting_metrics，则使用空数组。

6. risk_warnings：
   - 可以从 dimensions、data_limitations 和用户问题中提炼；
   - 风险提示必须克制、准确；
   - 可以使用“需要关注”“仍需观察”“存在不确定性”等表达；
   - 不得将“风险可控”改写为“风险较大”；
   - 不得夸大为“严重危机”“明显恶化”“高风险”，除非输入中明确这样判断；
   - 投资类问题必须包含“未覆盖估值、股价走势、行业景气度、市场情绪、个人风险偏好”等边界提示。

7. data_limitations：
   - 必须继承输入中的 data_limitations；
   - 不得删除；
   - 可以轻微润色；
   - markdown_report 中必须单独包含“数据限制”章节。

8. conclusion：
   - 必须基于 AnalysisAgent 的 summary、overall_score 和 conclusion 生成；
   - 可以压缩和报告化表达；
   - 不得新增未提供的事实；
   - 投资类问题不得输出直接买入、卖出或持有建议。

9. disclaimer：
   - 必须包含“不构成投资建议”；
   - 如果 report_type 为 investment_reference，免责声明需要更明确；
   - 免责声明应简洁、正式、克制。

10. markdown_report：
   - 必须是一份完整的 Markdown 格式正式报告；
   - 必须包含以下章节：
     # 标题
     ## 一、核心结论
     ## 二、总体评价
     ## 三、分维度分析
     ## 四、风险提示
     ## 五、数据限制
     ## 六、综合结论
     ## 七、免责声明
   - 分维度分析应覆盖 sections 中的所有章节；
   - markdown_report 中的内容必须与结构化字段一致；
   - 不得在 markdown_report 中加入结构化字段里不存在的重大判断；
   - 不得输出 Markdown 代码块。

一致性要求：
1. executive_summary、sections、risk_warnings、conclusion、markdown_report 必须相互一致；
2. markdown_report 中出现的关键指标必须来自 supporting_metrics；
3. 如果 data_limitations 指出缺少同比或行业对比数据，则不得在报告中强调同比增长、行业领先、行业较高水平等缺乏依据的表述；
4. 如果输入中存在内部表述冲突，应优先遵守 data_limitations，并使用更谨慎的表达；
5. 报告语言应专业、清晰、克制，避免营销化、绝对化、预测性表达。

输出要求：
1. 只输出严格 JSON；
2. 不要输出解释性文字；
3. JSON 必须包含以下完整字段：

{
  "status": "report_ready | report_partial | report_failed",
  "report_type": "financial_analysis | investment_reference | risk_analysis | general_report",
  "title": "报告标题",
  "executive_summary": "报告核心摘要",
  "overall_assessment": {
    "score": 数字或 null,
    "label": "评价标签",
    "basis": "评分依据",
    "confidence": "high | medium | low"
  },
  "sections": [
    {
      "heading": "章节标题",
      "summary": "章节小结",
      "key_points": ["要点1", "要点2"],
      "supporting_metrics": [
        {
          "name": "指标名称",
          "period": "报告期",
          "value": 数值或字符串,
          "unit": "单位"
        }
      ]
    }
  ],
  "risk_warnings": ["风险提示1", "风险提示2"],
  "data_limitations": ["数据限制1", "数据限制2"],
  "conclusion": "综合结论",
  "disclaimer": "免责声明",
  "markdown_report": "完整 Markdown 格式报告正文"
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
6. 不修改 supporting_metrics 中的 name、period、value、unit；
7. 不删除 data_limitations；
8. markdown_report 必须是一份完整、可直接展示给用户的正式 Markdown 报告；
9. 输出必须是严格 JSON，不要输出任何 JSON 以外的内容。
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

        return {
            "status": result.get("status"),
            "report_type": result.get("report_type"),
            "title": result.get("title"),
            "executive_summary": result.get("executive_summary") or "",
            "overall_assessment": result.get("overall_assessment") or {
                "score": overall_score.get("score"),
                "label": overall_score.get("label", ""),
                "basis": overall_score.get("basis", ""),
                "confidence": overall_score.get("confidence", "medium"),
            },
            "sections": result.get("sections"),
            "risk_warnings": result.get("risk_warnings") or [],
            "data_limitations": result.get("data_limitations") or analysis_result.get("data_limitations", []),
            "conclusion": result.get("conclusion") or analysis_result.get("conclusion") or "",
            "disclaimer": result.get("disclaimer") or "本报告仅基于已获取的公开财务数据和模型分析结果生成，不构成任何投资建议。",
            "markdown_report": result.get("markdown_report") or "",
        }

