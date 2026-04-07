"""Metric engine service."""

from app.tools.metric_tools import calculate_placeholder_metrics


class MetricEngineService:
    """Coordinates metric computation workflows."""

    def compute(self, payload: dict[str, object]) -> dict[str, object]:
        return calculate_placeholder_metrics(payload)
