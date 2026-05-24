# app/api/routes.py

from fastapi import APIRouter

from app.api.v1.financial_analysis import router as financial_analysis_router


api_router = APIRouter()

api_router.include_router(financial_analysis_router)