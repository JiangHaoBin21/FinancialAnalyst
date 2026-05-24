# app/api/v1/financial_analysis.py

from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_financial_analysis_runner
from app.application.financial_analysis_runner import FinancialAnalysisRunner
from app.models.schemas import (
    FinancialAnalysisRequest,
    FinancialAnalysisResponse,
)


router = APIRouter(
    prefix="/financial-analysis",
    tags=["Financial Analysis"],
)


@router.post(
    "",
    response_model=FinancialAnalysisResponse,
    status_code=status.HTTP_200_OK,
    summary="创建财务分析任务",
    description="提交用户问题，调用多 Agent 财务分析工作流，并返回分析报告结果。",
)
def create_financial_analysis(
    request: FinancialAnalysisRequest,
    runner: FinancialAnalysisRunner = Depends(get_financial_analysis_runner),
) -> dict:
    """创建并执行一次财务分析任务。

    第一版采用同步阻塞方式：
    - 请求进入后立即执行完整工作流
    - 工作流结束后直接返回报告
    """
    thread_id = request.thread_id or f"financial-analysis-{uuid4().hex}"

    try:
        result = runner.run(
            user_query=request.query,
            thread_id=thread_id,
        )

        payload = result.to_dict(include_state=request.include_state)
        payload["thread_id"] = thread_id

        return payload

    except TypeError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"财务分析工作流执行失败：{exc}",
        ) from exc