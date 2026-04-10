"""ReportAgent: 最小可运行 stub 版本。"""

from __future__ import annotations

from app.workflows.state import WorkflowState


class ReportAgent:
    """
    最小版 ReportAgent：
    - 不调用 LLM
    - 直接拼一份简单字符串报告
    """

    def run(self, state: WorkflowState) -> WorkflowState:
        print("[ReportAgent] running...")

        company = state.company_name or state.ts_code or "目标公司"
        summary = state.analysis_summary or "暂无分析摘要。"

        report = f"""# {company} 财务分析报告（Mock）

## 一、公司概况
- 公司名称：{state.company_profile.get("company_name", "未知")}
- 股票代码：{state.company_profile.get("ts_code", "未知")}
- 行业：{state.company_profile.get("industry", "未知")}

## 二、分析摘要
{summary}

## 三、结论
这是一个用于打通 workflow 的 mock 报告。
"""

        state.report_draft = report
        state.report_sections = {
            "company_profile": state.company_profile,
            "analysis_summary": summary,
        }
        state.final_report = report
        state.assistant_message = "ReportAgent 已生成 mock 报告。"
        return state