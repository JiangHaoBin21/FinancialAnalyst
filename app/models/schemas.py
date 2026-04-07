"""Application schemas."""

from dataclasses import dataclass


@dataclass(slots=True)
class AnalysisRequest:
    """Request schema for creating an analysis task."""

    ticker: str


@dataclass(slots=True)
class HealthResponse:
    """Response schema for health checks."""

    status: str
    service_name: str
