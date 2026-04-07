"""Reflection agent."""

from app.skills.reflection_skills import review_report


class ReflectionAgent:
    """Reviews intermediate results and suggests refinements."""

    def run(self, report: dict[str, object] | None = None) -> dict[str, object]:
        return review_report(report or {})
