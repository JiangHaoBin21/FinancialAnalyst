"""Skills for report generation."""

from app.tools.report_tools import render_report_payload


def compose_report(analysis: dict[str, object]) -> dict[str, object]:
    """Generate a report payload from analysis data."""
    return render_report_payload(analysis)
