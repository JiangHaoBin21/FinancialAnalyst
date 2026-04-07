"""Skills for report reflection."""

from app.tools.persistence_tools import build_review_snapshot


def review_report(report: dict[str, object]) -> dict[str, object]:
    """Return a placeholder review result."""
    snapshot = build_review_snapshot(report)
    return {"report": report, "snapshot": snapshot, "status": "reviewed"}
