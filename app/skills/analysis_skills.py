"""Skills for analysis generation."""

from app.tools.metric_tools import calculate_placeholder_metrics


def build_analysis_summary(payload: dict[str, object]) -> dict[str, object]:
    """Generate a placeholder analysis package."""
    metrics = calculate_placeholder_metrics(payload)
    return {"input": payload, "metrics": metrics, "summary": "analysis ready"}
