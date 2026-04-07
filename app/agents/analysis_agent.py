"""Analysis agent."""

from app.skills.analysis_skills import build_analysis_summary


class AnalysisAgent:
    """Builds analytical outputs from retrieved data."""

    def run(self, payload: dict[str, object] | None = None) -> dict[str, object]:
        return build_analysis_summary(payload or {})
