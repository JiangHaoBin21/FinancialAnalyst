"""Report agent."""

from app.skills.report_skills import compose_report


class ReportAgent:
    """Formats analysis results into report output."""

    def run(self, analysis: dict[str, object] | None = None) -> dict[str, object]:
        return compose_report(analysis or {})
