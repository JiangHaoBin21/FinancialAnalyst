"""AnalysisAgent: 最小可运行 stub 版本。"""

from __future__ import annotations

from app.workflows.state import WorkflowState


class AnalysisAgent:
    """
    最小版 AnalysisAgent：
    - 不做真实财务分析
    - 只基于 mock 数据写一点假结果
    """

    def run(self, state: WorkflowState) -> WorkflowState:
        print("[AnalysisAgent] running...")

        revenue = state.financial_data.get("revenue", [])
        net_profit = state.financial_data.get("net_profit", [])

        state.analysis_result = {
            "profitability": "good",
            "growth_trend": "upward",
            "revenue": revenue,
            "net_profit": net_profit,
        }

        state.analysis_summary = (
            "Mock analysis done: company shows stable growth and decent profitability."
        )

        state.assistant_message = "AnalysisAgent 已完成 mock 分析。"
        return state