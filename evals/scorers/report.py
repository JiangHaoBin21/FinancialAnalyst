"""Analysis 到 Report 的确定性一致性评分。"""

from __future__ import annotations

from typing import Any

from evals.models import MetricScore
from evals.scorers.common import (
    iter_supporting_metrics,
    metric_score,
    normalize_text,
    normalize_period,
    text_matches,
    units_equal,
    values_close,
)
from evals.scorers.limitations import classify_limitations


def _metric_key(metric: dict[str, Any]) -> tuple[str, str]:
    return normalize_text(metric.get("name")), normalize_period(metric.get("period"))


def _same_metric(left: dict[str, Any], right: dict[str, Any]) -> bool:
    return (
        _metric_key(left) == _metric_key(right)
        and values_close(left.get("value"), right.get("value"))
        and (
            not left.get("unit")
            or not right.get("unit")
            or units_equal(left.get("unit"), right.get("unit"))
        )
    )


def score_report_consistency(state: dict[str, Any]) -> MetricScore:
    analysis = state.get("analysis_result") or {}
    report = state.get("report_result") or {}
    analysis_score = analysis.get("overall_score") or {}
    report_score = report.get("overall_assessment") or {}
    analysis_metrics = list(iter_supporting_metrics(analysis.get("dimensions") or []))
    report_metrics = list(iter_supporting_metrics(report.get("sections") or []))
    analysis_limitation_types = classify_limitations(analysis.get("data_limitations") or [])
    report_limitation_types = classify_limitations(report.get("data_limitations") or [])
    markdown = str(report.get("markdown_report") or "")

    checks: dict[str, bool] = {
        "score_preserved": values_close(analysis_score.get("score"), report_score.get("score")),
        "label_preserved": text_matches(analysis_score.get("label"), report_score.get("label")),
        "confidence_preserved": normalize_text(analysis_score.get("confidence")) == normalize_text(report_score.get("confidence")),
        "limitation_types_preserved": analysis_limitation_types.issubset(report_limitation_types),
        "markdown_has_data_limitations": "数据限制" in markdown,
        "markdown_has_disclaimer": "免责声明" in markdown and "不构成投资建议" in markdown,
        "metrics_preserved": all(
            any(_same_metric(source, target) for target in report_metrics)
            for source in analysis_metrics
        ),
        "no_new_structured_metrics": all(
            any(_same_metric(source, target) for source in analysis_metrics)
            for target in report_metrics
        ),
    }
    return metric_score(
        sum(checks.values()),
        len(checks),
        checks=checks,
        analysis_metric_count=len(analysis_metrics),
        report_metric_count=len(report_metrics),
        analysis_limitations=analysis.get("data_limitations") or [],
        report_limitations=report.get("data_limitations") or [],
        analysis_limitation_types=sorted(analysis_limitation_types),
        report_limitation_types=sorted(report_limitation_types),
    )


def score_report_consistency_v1(state: dict[str, Any]) -> MetricScore:
    """第一迭代兼容口径：数据限制按原始文本包含关系核对。"""
    analysis = state.get("analysis_result") or {}
    report = state.get("report_result") or {}
    analysis_score = analysis.get("overall_score") or {}
    report_score = report.get("overall_assessment") or {}
    analysis_metrics = list(iter_supporting_metrics(analysis.get("dimensions") or []))
    report_metrics = list(iter_supporting_metrics(report.get("sections") or []))
    analysis_limitations = [normalize_text(item) for item in analysis.get("data_limitations") or []]
    report_limitations = [normalize_text(item) for item in report.get("data_limitations") or []]
    markdown = str(report.get("markdown_report") or "")
    checks = {
        "score_preserved": values_close(analysis_score.get("score"), report_score.get("score")),
        "label_preserved": text_matches(analysis_score.get("label"), report_score.get("label")),
        "confidence_preserved": normalize_text(analysis_score.get("confidence")) == normalize_text(report_score.get("confidence")),
        "limitations_preserved": all(
            any(source == target or source in target or target in source for target in report_limitations)
            for source in analysis_limitations
        ),
        "markdown_has_data_limitations": "数据限制" in markdown,
        "markdown_has_disclaimer": "免责声明" in markdown and "不构成投资建议" in markdown,
        "metrics_preserved": all(any(_same_metric(source, target) for target in report_metrics) for source in analysis_metrics),
        "no_new_structured_metrics": all(any(_same_metric(source, target) for source in analysis_metrics) for target in report_metrics),
    }
    return metric_score(sum(checks.values()), len(checks), checks=checks)
