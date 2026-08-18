"""数据规划、抓取完整性与 Analysis 证据利用评分。"""

from __future__ import annotations

from typing import Any

from evals.models import EvalCase, MetricScore
from evals.scorers.common import metric_score, parse_evidence


EVIDENCE_TOOL_PARTS: dict[str, set[str]] = {
    "income_statement_evidence_tool": {"income_statements"},
    "balance_sheet_evidence_tool": {"balance_sheets"},
    "cashflow_evidence_tool": {"cashflow_statements"},
    "fina_indicator_evidence_tool": {"financial_indicators"},
    "cross_statement_evidence_tool": {
        "income_statements", "balance_sheets", "cashflow_statements", "financial_indicators",
    },
}


def _ratio(numerator: int, denominator: int) -> float:
    return 1.0 if denominator == 0 else numerator / denominator


def score_data_completeness(case: EvalCase, state: dict[str, Any]) -> MetricScore:
    required_parts = set(case.expected.get("required_data_parts") or [])
    planned_parts = set(state.get("required_data_parts") or []) - {"company_profile"}
    financial_data = state.get("financial_data") or {}
    result = state.get("data_completeness_check_result") or {}
    detail_by_part = {
        detail.get("part_name"): detail
        for detail in result.get("part_details") or []
        if isinstance(detail, dict)
    }
    diagnostics: dict[str, Any] = {}
    for part in required_parts:
        records = financial_data.get(part) or []
        detail = detail_by_part.get(part) or {}
        has_records = bool(records)
        period_complete = bool(detail.get("is_complete")) if detail else has_records
        diagnostics[part] = {
            "record_count": len(records) if isinstance(records, list) else int(has_records),
            "missing_periods": detail.get("missing_periods") or [],
            "is_complete": period_complete,
        }

    evidence = parse_evidence((state.get("analysis_result") or {}).get("evidence"))
    used_parts: set[str] = set()
    evidence_tools: list[str] = []
    for round_result in evidence:
        tool_name = str(round_result.get("tool_name") or "")
        if tool_name:
            evidence_tools.append(tool_name)
            used_parts.update(EVIDENCE_TOOL_PARTS.get(tool_name, set()))

    true_plans = len(required_parts & planned_parts)
    plan_precision = _ratio(true_plans, len(planned_parts))
    plan_recall = _ratio(true_plans, len(required_parts))
    complete_parts = sum(
        bool(detail.get("record_count")) and bool(detail.get("is_complete"))
        for detail in diagnostics.values()
    )
    fetch_completeness = _ratio(complete_parts, len(required_parts))
    evidence_utilization = _ratio(len(required_parts & used_parts), len(required_parts))
    component_values = {
        "planning_precision": plan_precision,
        "planning_recall": plan_recall,
        "fetch_completeness": fetch_completeness,
        "evidence_utilization": evidence_utilization,
    }
    return metric_score(
        sum(component_values.values()),
        len(component_values),
        components={name: round(value * 100, 2) for name, value in component_values.items()},
        expected_parts=sorted(required_parts),
        planned_parts=sorted(planned_parts),
        evidence_used_parts=sorted(used_parts),
        evidence_tools=evidence_tools,
        parts=diagnostics,
    )


def score_data_completeness_v1(case: EvalCase, state: dict[str, Any]) -> MetricScore:
    """第一迭代兼容口径：数据非空 + 期间完整。"""
    required_parts = list(case.expected.get("required_data_parts") or [])
    financial_data = state.get("financial_data") or {}
    result = state.get("data_completeness_check_result") or {}
    detail_by_part = {
        detail.get("part_name"): detail
        for detail in result.get("part_details") or []
        if isinstance(detail, dict)
    }
    checks: dict[str, bool] = {}
    diagnostics: dict[str, Any] = {}
    for part in required_parts:
        records = financial_data.get(part) or []
        detail = detail_by_part.get(part) or {}
        has_records = bool(records)
        period_complete = bool(detail.get("is_complete")) if detail else has_records
        checks[f"{part}:non_empty"] = has_records
        checks[f"{part}:period_complete"] = period_complete
        diagnostics[part] = {
            "record_count": len(records) if isinstance(records, list) else int(has_records),
            "missing_periods": detail.get("missing_periods") or [],
            "is_complete": period_complete,
        }
    return metric_score(
        sum(checks.values()),
        len(checks) or 1,
        checks=checks,
        parts=diagnostics,
    )
