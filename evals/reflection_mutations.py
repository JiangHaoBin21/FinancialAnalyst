"""Reflection 缺陷注入、数据集构建、在线审查与确定性评分。"""

from __future__ import annotations

import copy
import re
import statistics
from datetime import datetime
from pathlib import Path
from time import perf_counter
from typing import Any

from evals.io_utils import read_json, write_json
from evals.telemetry import TimedLLMProxy


def expand_mutation_matrix(matrix: dict[str, Any]) -> list[dict[str, Any]]:
    specs = []
    for source_case_id in matrix.get("source_case_ids") or []:
        for mutation in matrix.get("mutations") or []:
            mutation_type = str(mutation["type"])
            specs.append(
                {
                    **dict(mutation),
                    "source_case_id": str(source_case_id),
                    "mutation_id": f"{source_case_id}__{mutation_type}",
                }
            )
    return specs


def build_mutation_dataset(
    source_experiment_dir: Path,
    output_dir: Path,
    matrix: dict[str, Any],
) -> dict[str, Any]:
    specs = expand_mutation_matrix(matrix)
    built = []
    skipped = []
    for spec in specs:
        source_path = source_experiment_dir / "raw" / f"{spec['source_case_id']}.json"
        if not source_path.exists():
            skipped.append({"mutation_id": spec["mutation_id"], "reason": "source_missing"})
            continue
        source = read_json(source_path)
        state = source.get("state") or {}
        if not _is_delivered_state(state):
            skipped.append({"mutation_id": spec["mutation_id"], "reason": "source_not_delivered"})
            continue
        mutated_state = apply_mutation(state, str(spec["type"]))
        write_json(
            output_dir / "inputs" / f"{spec['mutation_id']}.json",
            {
                "schema_version": 2,
                "spec": spec,
                "source_experiment_dir": str(source_experiment_dir.resolve()),
                "state": mutated_state,
            },
        )
        built.append(spec["mutation_id"])
    manifest = {
        "schema_version": 2,
        "experiment_type": "reflection_mutation",
        "created_at": datetime.now().astimezone().isoformat(),
        "source_experiment_dir": str(source_experiment_dir.resolve()),
        "requested_count": len(specs),
        "built_count": len(built),
        "skipped_count": len(skipped),
        "mutation_ids": built,
        "skipped": skipped,
    }
    write_json(output_dir / "manifest.json", manifest)
    return manifest


def apply_mutation(state: dict[str, Any], mutation_type: str) -> dict[str, Any]:
    mutated = copy.deepcopy(state)
    report = mutated.setdefault("report_result", {})
    analysis = mutated.get("analysis_result") or {}
    markdown = str(report.get("markdown_report") or "")

    if mutation_type == "clean_control":
        return mutated
    if mutation_type == "unsupported_claim":
        claim = "公司已获得未来三年锁定订单，利润将持续高速增长。"
        report.setdefault("sections", []).append(
            {"heading": "未来展望", "summary": claim, "key_points": [claim], "supporting_metrics": []}
        )
        report["markdown_report"] = f"{markdown}\n\n## 未来展望\n\n{claim}"
    elif mutation_type == "overstatement":
        report["conclusion"] = "综合财务表现完全优秀，未来业绩必然持续增长且不存在重大风险。"
        report["markdown_report"] = f"{markdown}\n\n未来业绩必然持续增长且不存在重大风险。"
    elif mutation_type == "direct_investment_instruction":
        report["conclusion"] = "综合上述财务表现，建议立即买入并长期持有。"
        report["markdown_report"] = f"{markdown}\n\n建议立即买入并长期持有。"
    elif mutation_type == "data_limitation_missing":
        report["data_limitations"] = []
        report["markdown_report"] = _remove_markdown_section(markdown, "数据限制")
    elif mutation_type == "company_info_error":
        report["title"] = "错误公司（000001.SZ）财务分析报告"
        report["markdown_report"] = re.sub(
            r"^#\s+.*$", "# 错误公司（000001.SZ）财务分析报告", markdown, count=1, flags=re.MULTILINE
        )
    elif mutation_type == "missing_user_intent":
        report["sections"] = []
        report["executive_summary"] = "本报告仅列示基础信息，未回答用户提出的分析问题。"
        report["markdown_report"] = "# 财务报告\n\n仅列示公司基础信息。\n\n## 免责声明\n本报告不构成投资建议。"
    elif mutation_type == "missing_analysis_focus":
        sections = list(report.get("sections") or [])
        if sections:
            report["sections"] = sections[1:]
            heading = str(sections[0].get("heading") or "")
            report["markdown_report"] = _remove_markdown_section(markdown, heading)
        else:
            report["markdown_report"] = "# 财务报告\n\n未覆盖分析重点。"
    elif mutation_type == "structure_or_readability":
        report["markdown_report"] = "财务报告：" + re.sub(r"[#|*\n]+", " ", markdown)[:500]
    elif mutation_type == "input_invalid":
        mutated["report_result"] = {}
    else:
        raise ValueError(f"未知 mutation type: {mutation_type}")

    # 保留 Analysis 作为唯一事实基线；所有注入只作用于 Report。
    mutated["analysis_result"] = analysis
    return mutated


def run_reflection_input(
    input_path: Path,
    output_dir: Path,
    *,
    pricing: dict[str, Any] | None = None,
    rerun: bool = False,
) -> dict[str, Any]:
    output_path = output_dir / "raw" / input_path.name
    if output_path.exists() and not rerun:
        return read_json(output_path)
    from app.agents.reflection_agent import ReflectionAgent
    from app.llms.openai_client import OpenAIClient

    payload = read_json(input_path)
    proxy = TimedLLMProxy(OpenAIClient(), pricing=pricing)
    started = perf_counter()
    try:
        result = ReflectionAgent(proxy).run(payload["state"])
        run_status = "completed"
        exception = None
    except Exception as exc:
        result = {}
        run_status = "failed"
        exception = {"type": type(exc).__name__, "message": str(exc)}
    runtime = proxy.snapshot()
    runtime["end_to_end_latency_ms"] = round((perf_counter() - started) * 1000, 2)
    scored = score_reflection_result(payload["spec"], result, run_status=run_status)
    output = {
        "schema_version": 2,
        "mutation_id": payload["spec"]["mutation_id"],
        "spec": payload["spec"],
        "run_status": run_status,
        "reflection_result": result,
        "runtime": runtime,
        "score": scored,
        "exception": exception,
    }
    write_json(output_path, output)
    write_json(output_dir / "scores" / input_path.name, scored)
    return output


def score_reflection_result(
    spec: dict[str, Any],
    result: dict[str, Any],
    *,
    run_status: str = "completed",
) -> dict[str, Any]:
    expected_types = set(spec.get("expected_issue_types") or [])
    actual_types = {
        str(issue.get("type"))
        for issue in result.get("issues") or []
        if isinstance(issue, dict) and issue.get("type")
    }
    expected_route = spec.get("expected_route")
    expected_routes = set(expected_route if isinstance(expected_route, list) else [expected_route])
    expected_decisions = set(spec.get("acceptable_decisions") or [])
    clean = not expected_types
    checks = {
        "call_completed": run_status == "completed",
        "decision_correct": result.get("decision") in expected_decisions,
        "route_correct": result.get("recommended_next_stage") in expected_routes,
        "issue_detection_correct": not actual_types if clean else bool(expected_types & actual_types),
    }
    issue_precision = (
        1.0 if not actual_types and clean else len(expected_types & actual_types) / len(actual_types)
        if actual_types else 0.0
    )
    # 单个 mutation 可能允许 Reflection 使用多个等价 issue type；这里衡量
    # “是否检出该缺陷”，而不是要求把所有同义标签同时报出。
    issue_recall = 1.0 if clean and not actual_types else (
        float(bool(expected_types & actual_types)) if expected_types else 0.0
    )
    score = 100 * statistics.fmean([float(value) for value in checks.values()])
    return {
        "mutation_id": spec.get("mutation_id"),
        "source_case_id": spec.get("source_case_id"),
        "mutation_type": spec.get("type"),
        "score": round(score, 2),
        "checks": checks,
        "expected_issue_types": sorted(expected_types),
        "actual_issue_types": sorted(actual_types),
        "issue_precision": round(issue_precision, 4),
        "issue_recall": round(issue_recall, 4),
    }


def aggregate_reflection_results(output_dir: Path) -> dict[str, Any]:
    payloads = [read_json(path) for path in sorted((output_dir / "raw").glob("*.json"))]
    if not payloads:
        raise ValueError(f"没有 Reflection 运行产物: {output_dir / 'raw'}")
    scores = [payload["score"] for payload in payloads]
    faulty = [score for score in scores if score.get("expected_issue_types")]
    clean = [score for score in scores if not score.get("expected_issue_types")]
    summary = {
        "case_count": len(scores),
        "mean_score": round(statistics.fmean(score["score"] for score in scores), 2),
        "defect_detection_recall": round(
            100 * statistics.fmean(score["issue_recall"] for score in faulty), 2
        ) if faulty else None,
        "issue_precision": round(
            100 * statistics.fmean(score["issue_precision"] for score in faulty), 2
        ) if faulty else None,
        "clean_false_positive_rate": round(
            100 * statistics.fmean(bool(score["actual_issue_types"]) for score in clean), 2
        ) if clean else None,
        "decision_accuracy": round(
            100 * statistics.fmean(score["checks"]["decision_correct"] for score in scores), 2
        ),
        "route_accuracy": round(
            100 * statistics.fmean(score["checks"]["route_correct"] for score in scores), 2
        ),
    }
    write_json(output_dir / "summary.json", summary)
    return summary


def _is_delivered_state(state: dict[str, Any]) -> bool:
    return bool(
        isinstance(state.get("analysis_result"), dict)
        and isinstance(state.get("report_result"), dict)
        and (state.get("report_result") or {}).get("markdown_report")
    )


def _remove_markdown_section(markdown: str, heading: str) -> str:
    if not heading:
        return markdown
    pattern = rf"(?ms)^##+\s*{re.escape(heading)}\s*$.*?(?=^##+\s|\Z)"
    return re.sub(pattern, "", markdown).strip()
