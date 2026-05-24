# app/main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import api_router


app = FastAPI(
    title="Multi-Agent Financial Analysis API",
    description="基于 LangGraph 的多 Agent 财务分析系统接口服务",
    version="0.1.0",
)


# 开发阶段先放开跨域，方便后续前端本地调试。
# 正式部署时建议改成具体前端地址，例如 http://localhost:3000。
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(api_router, prefix="/api/v1")


@app.get("/health", summary="健康检查")
def health_check() -> dict:
    return {"status": "ok"}