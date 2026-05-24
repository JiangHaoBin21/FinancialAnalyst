# app/schemas/financial_analysis.py

from typing import Any

from pydantic import BaseModel, Field


class FinancialAnalysisRequest(BaseModel):
    """创建财务分析任务的请求体。"""

    query: str = Field(..., min_length=1, description="用户原始问题，例如：宁德时代2023年度财务分析")
    thread_id: str | None = Field(default=None, description="可选。不传则由后端自动生成")
    include_state: bool = Field(default=False, description="是否在响应中返回完整工作流状态，调试时可开启")


class FinancialAnalysisResponse(BaseModel):
    """财务分析任务的响应体。"""

    thread_id: str
    status: str | None = None
    current_stage: str | None = None
    next_step: str | None = None
    needs_user_input: bool = False
    has_error: bool = False
    assistant_message: str | None = None
    error_message: str | None = None
    final_report: str | None = None
    analysis_result: dict[str, Any] = Field(default_factory=dict)
    report_result: dict[str, Any] = Field(default_factory=dict)
    execution_history: list[dict[str, Any]] = Field(default_factory=list)


class ErrorResponse(BaseModel):
    """统一错误响应。"""

    detail: str