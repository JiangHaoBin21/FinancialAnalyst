"""用户意图和要求维度覆盖评分。"""

from __future__ import annotations

from typing import Any

from evals.models import EvalCase, MetricScore
from evals.scorers.common import DIMENSION_ALIASES, metric_score, normalize_text


def score_intent_coverage(case: EvalCase, state: dict[str, Any]) -> MetricScore:
    required = list(case.expected.get("required_dimensions") or [])
    analysis = state.get("analysis_result") or {}
    report = state.get("report_result") or {}
    searchable_parts: list[str] = []
    for dimension in analysis.get("dimensions") or []:
        if isinstance(dimension, dict):
            searchable_parts.append(str(dimension.get("name") or ""))
    for section in report.get("sections") or []:
        if isinstance(section, dict):
            searchable_parts.append(str(section.get("heading") or ""))
    searchable_parts.extend(str(item) for item in report.get("risk_warnings") or [])
    searchable = normalize_text(" ".join(searchable_parts))

    coverage: dict[str, bool] = {}
    for dimension in required:
        aliases = DIMENSION_ALIASES.get(dimension, (dimension,))
        coverage[dimension] = any(normalize_text(alias) in searchable for alias in aliases)
    return metric_score(
        sum(coverage.values()),
        len(required) or 1,
        required=required,
        coverage=coverage,
        observed_headings=searchable_parts,
    )
