"""AnalysisAgent: minimal analysis implementation."""

from __future__ import annotations

from app.workflows.state import WorkflowState


class AnalysisAgent:
    """Produces a simple analysis from merged financial data."""

    def run(self, state: WorkflowState) -> dict:
        print("[AnalysisAgent] running...")

        financial_data = state.get("financial_data", {})
        income = financial_data.get("income_statements", {})
        indicators = financial_data.get("financial_indicators", {})

        revenue = income.get("revenue", [])
        net_profit = income.get("net_profit", [])

        analysis_result = {
            "profitability": "good" if net_profit else "unknown",
            "growth_trend": "upward" if revenue else "unknown",
            "revenue": revenue,
            "net_profit": net_profit,
            "indicator_snapshot": indicators,
        }

        return {
            "analysis_result": analysis_result,
            "analysis_summary": (
                "Mock analysis done: company shows stable growth and decent profitability."
            ),
            "assistant_message": "AnalysisAgent completed mock analysis.",
        }
