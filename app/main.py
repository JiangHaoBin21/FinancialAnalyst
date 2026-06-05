# app/main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import api_router


app = FastAPI(
    title="Multi-Agent Financial Analysis API",
    description="基于 LangGraph 的多 Agent 财务分析系统接口服务",
    version="0.1.0",
)


# 开发阶段允许本地 Vite 前端访问。
# 当前接口不依赖 Cookie，关闭 credentials 可避免浏览器拒绝通配 origin + credentials 的组合。
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5173",
        "http://localhost:5173",
        "http://127.0.0.1:4173",
        "http://localhost:4173",
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)


app.include_router(api_router, prefix="/api/v1")


@app.get("/health", summary="健康检查")
def health_check() -> dict:
    return {"status": "ok"}
