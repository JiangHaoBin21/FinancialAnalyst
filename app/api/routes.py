"""API route definitions."""

from app.api.deps import get_runtime_context
from app.models.schemas import AnalysisRequest, HealthResponse


def register_routes() -> list[str]:
    """Return the route names exposed by the API layer."""
    return ["health_check", "analysis", "report"]


def health_check() -> HealthResponse:
    """Return a simple health payload."""
    context = get_runtime_context()
    return HealthResponse(status="ok", service_name=context["app_name"])


def create_analysis(request: AnalysisRequest) -> dict[str, str]:
    """Return a placeholder analysis task response."""
    return {"task": "analysis", "ticker": request.ticker, "status": "queued"}
