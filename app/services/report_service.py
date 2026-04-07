"""Report generation service."""

from app.tools.report_tools import render_report_payload


class ReportService:
    """Creates report payloads from analysis outputs."""

    def generate(self, analysis: dict[str, object] | None = None) -> dict[str, object]:
        return render_report_payload(analysis or {})
