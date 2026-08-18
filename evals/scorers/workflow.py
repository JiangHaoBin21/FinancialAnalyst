"""工作流与交付物结构评分。"""

from __future__ import annotations

from typing import Any

from evals.models import EvalCase, MetricScore
from evals.scorers.common import json_safe, metric_score, normalize_text


ANALYSIS_KEYS = {"status", "summary", "dimensions", "data_limitations", "evidence", "conclusion"}
REPORT_KEYS = {
    "status", "report_type", "title", "executive_summary", "overall_assessment",
    "sections", "risk_warnings", "data_limitations", "conclusion", "disclaimer", "markdown_report",
}


def score_workflow(case: EvalCase, state: dict[str, Any]) -> MetricScore:
    expected = case.expected
    outcomes = set(expected.get("outcomes") or ["finished"])
    history = state.get("execution_history") or []
    successful_agents = {
        record.get("agent")
        for record in history
        if isinstance(record, dict) and record.get("success")
    }
    required_agents = set(expected.get("required_agents") or [])
    analysis = state.get("analysis_result") or {}
    report = state.get("report_result") or {}

    deliverable_required = bool(expected.get("deliverable_required", True))
    error_allowed = bool(expected.get("error_allowed", False))
    checks: dict[str, bool] = {
        "expected_outcome": state.get("status") in outcomes,
        "no_unexpected_workflow_error": error_allowed or not state.get("has_error"),
        "required_agents": required_agents.issubset(successful_agents),
        "json_safe_state": json_safe(state),
    }
    if deliverable_required:
        checks["analysis_schema"] = isinstance(analysis, dict) and ANALYSIS_KEYS.issubset(analysis)
        checks["report_schema"] = isinstance(report, dict) and REPORT_KEYS.issubset(report)
    else:
        checks["no_unexpected_deliverable"] = not report.get("markdown_report")
    if expected.get("ts_code"):
        checks["ticker_resolved"] = normalize_text(state.get("ts_code")) == normalize_text(expected["ts_code"])
    if expected.get("company_name"):
        actual_company = state.get("company_name") or (state.get("company_profile") or {}).get("name") or (state.get("company_profile") or {}).get("company_name")
        expected_company = normalize_text(expected["company_name"])
        actual_company_text = normalize_text(actual_company)
        checks["company_resolved"] = bool(
            actual_company_text
            and (expected_company in actual_company_text or actual_company_text in expected_company)
        )
    expected_time = expected.get("time_range") or {}
    actual_time = state.get("time_range") or {}
    if expected_time:
        checks["time_range_resolved"] = (
            int(actual_time.get("start_year") or -1) == int(expected_time.get("start_year") or -2)
            and int(actual_time.get("end_year") or -1) == int(expected_time.get("end_year") or -2)
        )
    passed = sum(bool(value) for value in checks.values())
    return metric_score(
        passed,
        len(checks),
        checks=checks,
        successful_agents=sorted(str(agent) for agent in successful_agents if agent),
        missing_agents=sorted(required_agents - successful_agents),
    )


def invalid_deliverable(state: dict[str, Any], *, deliverable_required: bool = True) -> bool:
    if not deliverable_required:
        return False
    analysis = state.get("analysis_result")
    report = state.get("report_result")
    return not (
        isinstance(analysis, dict)
        and ANALYSIS_KEYS.issubset(analysis)
        and isinstance(report, dict)
        and REPORT_KEYS.issubset(report)
        and isinstance(report.get("markdown_report"), str)
        and bool(report["markdown_report"].strip())
    )
