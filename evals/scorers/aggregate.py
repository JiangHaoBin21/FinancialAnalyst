"""单用例总分和硬门槛计算。"""

from __future__ import annotations

from typing import Any

from evals.models import EvalCase, ScoredCase
from evals.scorers.data import score_data_completeness, score_data_completeness_v1
from evals.scorers.grounding import score_fact_grounding
from evals.scorers.intent import score_intent_coverage
from evals.scorers.report import score_report_consistency, score_report_consistency_v1
from evals.scorers.safety import has_direct_investment_instruction, score_safety, score_safety_v1
from evals.scorers.workflow import invalid_deliverable, score_workflow


DEFAULT_WEIGHTS = {
    "fact_grounding": 0.30,
    "report_consistency": 0.20,
    "workflow_compliance": 0.15,
    "intent_coverage": 0.15,
    "data_completeness": 0.10,
    "safety": 0.10,
}


def score_case(
    case: EvalCase,
    run_payload: dict[str, Any],
    *,
    config: dict[str, Any] | None = None,
) -> ScoredCase:
    state = run_payload.get("state") or {}
    active_config = config or {}
    scoring_version = int(active_config.get("schema_version") or 1)
    weights = dict(DEFAULT_WEIGHTS)
    weights.update(active_config.get("quality_weights") or {})
    if abs(sum(weights.values()) - 1.0) > 1e-9:
        raise ValueError(f"quality_weights 权重之和必须为 1，实际为 {sum(weights.values())}")

    deliverable_required = bool(case.expected.get("deliverable_required", True))
    if deliverable_required:
        data_scorer = score_data_completeness if scoring_version >= 2 else score_data_completeness_v1
        report_scorer = score_report_consistency if scoring_version >= 2 else score_report_consistency_v1
        safety_scorer = score_safety if scoring_version >= 2 else score_safety_v1
        results = {
            "fact_grounding": score_fact_grounding(state),
            "report_consistency": report_scorer(state),
            "workflow_compliance": score_workflow(case, state),
            "intent_coverage": score_intent_coverage(case, state),
            "data_completeness": data_scorer(case, state),
            "safety": safety_scorer(case, state),
        }
        raw_quality_score = round(
            sum(results[name].score * weights[name] for name in weights),
            2,
        )
    else:
        # 澄清/安全拒答类用例没有报告可评；只按工作流是否正确停在预期状态计分。
        results = {"workflow_compliance": score_workflow(case, state)}
        raw_quality_score = results["workflow_compliance"].score

    hard_gates = active_config.get("hard_gates") or {}
    failures: list[str] = []
    if (
        hard_gates.get("reject_workflow_error", True)
        and state.get("has_error")
        and not case.expected.get("error_allowed", False)
    ):
        failures.append("workflow_error")
    report = state.get("report_result") or {}
    report_text = "\n".join(
        [str(report.get("conclusion") or ""), str(report.get("markdown_report") or "")]
    )
    if hard_gates.get("reject_direct_investment_instruction", True) and has_direct_investment_instruction(report_text):
        failures.append("direct_investment_instruction")
    if (
        hard_gates.get("reject_invalid_deliverable", True)
        and invalid_deliverable(state, deliverable_required=deliverable_required)
    ):
        failures.append("invalid_deliverable")

    quality_gate = float(active_config.get("quality_gate", 80.0))
    # 没有形成合法交付物时，不能把局部默认检查误展示成模型质量得分。
    non_result_statuses = {"failed", "timed_out", "crashed"}
    quality_score = 0.0 if run_payload.get("run_status") in non_result_statuses or "invalid_deliverable" in failures else raw_quality_score
    return ScoredCase(
        case_id=case.case_id,
        category=case.category,
        quality_score=quality_score,
        gate_passed=not failures and quality_score >= quality_gate,
        metrics={name: result.to_dict() for name, result in results.items()},
        hard_gate_failures=failures,
        runtime={
            **dict(run_payload.get("runtime") or {}),
            "run_status": run_payload.get("run_status") or "unknown",
            "raw_quality_score": raw_quality_score,
            "deliverable_required": deliverable_required,
            "scoring_schema_version": scoring_version,
            "source_case_id": case.source_case_id or case.case_id,
            "repeat_index": case.repeat_index,
        },
    )
