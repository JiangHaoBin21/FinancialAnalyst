# app/api/deps.py

from functools import lru_cache

from app.application.financial_analysis_runner import FinancialAnalysisRunner


@lru_cache(maxsize=1)
def get_financial_analysis_runner() -> FinancialAnalysisRunner:
    """获取财务分析工作流运行器。

    使用 lru_cache 是为了让 Runner 在应用生命周期内复用。
    Runner 内部会懒加载 workflow_graph，避免每次请求都重新构建图。
    """
    return FinancialAnalysisRunner()