"""DataAgent: 最小可运行 stub 版本。"""

from __future__ import annotations

from app.workflows.state import WorkflowState


class DataAgent:
    """
    最小版 DataAgent：
    - 仅用于打通工作流
    - 不接真实数据库 / TuShare
    - 只打印 + 写入少量 mock 数据
    """

    def run(self, state: WorkflowState) -> WorkflowState:
        print("[DataAgent] running...")

        state.company_profile = {
            "company_name": state.company_name or "MockCompany",
            "ts_code": state.ts_code or "000001.SZ",
            "industry": "Mock Industry",
        }

        state.financial_data = {
            "revenue": [100, 120, 150],
            "net_profit": [20, 25, 32],
            "assets": [200, 230, 260],
        }

        state.data_summary = {
            "message": "Mock financial data prepared."
        }

        state.assistant_message = "DataAgent 已完成 mock 数据准备。"
        return state