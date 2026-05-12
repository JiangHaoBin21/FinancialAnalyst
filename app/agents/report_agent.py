"""ReportAgent: minimal report generation implementation."""

from __future__ import annotations

from app.workflows.state import WorkflowState


class ReportAgent:
    """Builds a simple report from analysis output."""

    def run(self, state: WorkflowState) -> dict:
        print("[ReportAgent] 正在执行...")

        company = state.get("company_name") or state.get("ts_code") or "TargetCompany"
        company_profile = state.get("company_profile", {})
        summary = state.get("analysis_summary") or "No analysis summary available."

        report = f"""# {company} Financial Analysis Report (Mock)

## Company Profile
- Company: {company_profile.get("company_name", "Unknown")}
- Ticker: {company_profile.get("ts_code", "Unknown")}
- Industry: {company_profile.get("industry", "Unknown")}

## Analysis Summary
{summary}

## Conclusion
This is a mock report used to validate the LangGraph workflow.
"""

        return {
            "report_draft": report,
            "report_sections": {
                "company_profile": company_profile,
                "analysis_summary": summary,
            },
            "final_report": report,
            "assistant_message": "ReportAgent 生成模拟报告。",
        }
