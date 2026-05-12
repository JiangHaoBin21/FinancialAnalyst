"""AnalysisAgent: minimal analysis implementation."""

from __future__ import annotations

from app.workflows.state import WorkflowState


class AnalysisAgent:
    """Produces a simple analysis from merged financial data."""

    def run(self, state: WorkflowState) -> dict:
        print("[AnalysisAgent] 正在执行...")

        financial_data = state.get("financial_data", {})
        income = list(_iter_records(financial_data.get("income_statements", [])))
        indicators = list(_iter_records(financial_data.get("financial_indicators", [])))

        revenue = [record.get("revenue") for record in income if record.get("revenue") is not None]
        net_profit = [record.get("net_profit") for record in income if record.get("net_profit") is not None]

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
                "模拟分析完成：公司增长较稳定，盈利能力表现尚可。"
            ),
            "assistant_message": "AnalysisAgent 完成模拟分析。",
        }


def _iter_records(records):
    if isinstance(records, list):
        for record in records:
            yield from _iter_records(record)
        return
    if isinstance(records, dict):
        yield records
