"""评测聚合、CSV 与 Markdown 报告生成。"""

from __future__ import annotations

import csv
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from evals.io_utils import write_json
from evals.models import ScoredCase
from evals.statistics import bootstrap_mean_ci


def percentile(values: list[float], quantile: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return round(ordered[0], 2)
    position = (len(ordered) - 1) * quantile
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = position - lower
    return round(ordered[lower] * (1 - fraction) + ordered[upper] * fraction, 2)


def aggregate_scores(
    scores: list[ScoredCase],
    *,
    bootstrap_config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    metric_values: dict[str, list[float]] = defaultdict(list)
    delivered_metric_values: dict[str, list[float]] = defaultdict(list)
    category_values: dict[str, list[float]] = defaultdict(list)
    latencies: list[float] = []
    failure_counts: Counter[str] = Counter()
    run_status_counts: Counter[str] = Counter()
    delivered_scores: list[float] = []
    successful_outcome_count = 0
    total_tokens: list[float] = []
    estimated_costs: list[float] = []
    llm_latencies: list[float] = []
    usage_covered_cases = 0
    repeat_quality: dict[str, list[float]] = defaultdict(list)
    repeat_gate_passes: dict[str, list[bool]] = defaultdict(list)
    llm_stage_totals: dict[str, dict[str, float]] = defaultdict(
        lambda: {"call_count": 0.0, "latency_ms": 0.0, "prompt_tokens": 0.0, "completion_tokens": 0.0, "total_tokens": 0.0}
    )

    for score in scores:
        run_status_counts[str(score.runtime.get("run_status") or "unknown")] += 1
        source_case_id = str(score.runtime.get("source_case_id") or score.case_id)
        repeat_quality[source_case_id].append(score.quality_score)
        repeat_gate_passes[source_case_id].append(score.gate_passed)
        category_values[score.category].append(score.quality_score)
        for name, metric in score.metrics.items():
            metric_values[name].append(float(metric["score"]))
        latency = score.runtime.get("end_to_end_latency_ms")
        if isinstance(latency, (int, float)):
            latencies.append(float(latency))
        llm_latency = score.runtime.get("llm_latency_ms")
        if isinstance(llm_latency, (int, float)):
            llm_latencies.append(float(llm_latency))
        tokens = score.runtime.get("total_tokens")
        if score.runtime.get("token_usage_available") and isinstance(tokens, (int, float)):
            total_tokens.append(float(tokens))
            usage_covered_cases += 1
        cost = score.runtime.get("estimated_cost")
        if score.runtime.get("estimated_cost_available") and isinstance(cost, (int, float)):
            estimated_costs.append(float(cost))
        for stage, stage_values in (score.runtime.get("llm_stage_usage") or {}).items():
            bucket = llm_stage_totals[str(stage)]
            for name in bucket:
                value = stage_values.get(name)
                if isinstance(value, (int, float)):
                    bucket[name] += float(value)
        failure_counts.update(score.hard_gate_failures)
        workflow_checks = (
            score.metrics.get("workflow_compliance", {}).get("details", {}).get("checks", {})
        )
        outcome_success = bool(workflow_checks.get("expected_outcome")) and not {
            "workflow_error", "invalid_deliverable"
        }.intersection(score.hard_gate_failures)
        successful_outcome_count += int(outcome_success)
        delivered = bool(score.runtime.get("deliverable_required", True)) and outcome_success
        if delivered:
            delivered_scores.append(score.quality_score)
            for name, metric in score.metrics.items():
                delivered_metric_values[name].append(float(metric["score"]))

    boot = dict(bootstrap_config or {})
    bootstrap_kwargs = {
        "samples": int(boot.get("samples", 5000)),
        "confidence_level": float(boot.get("confidence_level", 0.95)),
        "seed": int(boot.get("seed", 20260813)),
    }
    quality_values = [s.quality_score for s in scores]
    repeated_groups = {
        case_id: values for case_id, values in repeat_quality.items() if len(values) > 1
    }
    within_case_stddevs = [statistics.stdev(values) for values in repeated_groups.values()]
    return {
        "case_count": len(scores),
        "quality_score_mean": round(statistics.fmean(s.quality_score for s in scores), 2) if scores else None,
        "delivered_quality_score_mean": (
            round(statistics.fmean(delivered_scores), 2)
            if delivered_scores
            else None
        ),
        "quality_score_min": round(min((s.quality_score for s in scores), default=0.0), 2) if scores else None,
        "quality_score_stddev": (
            round(statistics.stdev(quality_values), 2) if len(quality_values) > 1 else 0.0 if quality_values else None
        ),
        "quality_score_confidence_interval": bootstrap_mean_ci(
            quality_values, **bootstrap_kwargs
        ),
        "repeat_stability": {
            "repeated_source_case_count": len(repeated_groups),
            "repeats_per_case": sorted({len(values) for values in repeated_groups.values()}),
            "mean_within_case_stddev": (
                round(statistics.fmean(within_case_stddevs), 2) if within_case_stddevs else None
            ),
            "all_repeats_gate_pass_rate": (
                round(
                    100 * sum(all(repeat_gate_passes[case_id]) for case_id in repeated_groups) / len(repeated_groups),
                    2,
                ) if repeated_groups else None
            ),
        },
        "workflow_success_rate": (
            round(100 * successful_outcome_count / len(scores), 2)
            if scores
            else None
        ),
        "gate_pass_rate": round(100 * sum(s.gate_passed for s in scores) / len(scores), 2) if scores else None,
        "metric_means": {
            name: round(statistics.fmean(values), 2)
            for name, values in sorted(metric_values.items())
        },
        "delivered_metric_means": {
            name: round(statistics.fmean(values), 2)
            for name, values in sorted(delivered_metric_values.items())
        },
        "category_means": {
            category: round(statistics.fmean(values), 2)
            for category, values in sorted(category_values.items())
        },
        "latency_ms": {
            "p50": percentile(latencies, 0.50),
            "p95": percentile(latencies, 0.95),
            "mean": round(statistics.fmean(latencies), 2) if latencies else None,
        },
        "llm_latency_ms": {
            "p50": percentile(llm_latencies, 0.50),
            "p95": percentile(llm_latencies, 0.95),
            "mean": round(statistics.fmean(llm_latencies), 2) if llm_latencies else None,
        },
        "token_usage": {
            "covered_case_count": usage_covered_cases,
            "coverage_rate": round(100 * usage_covered_cases / len(scores), 2) if scores else None,
            "total": int(sum(total_tokens)) if total_tokens else None,
            "mean_per_covered_case": round(statistics.fmean(total_tokens), 2) if total_tokens else None,
            "p50_per_case": percentile(total_tokens, 0.50),
            "p95_per_case": percentile(total_tokens, 0.95),
        },
        "estimated_cost": {
            "covered_case_count": len(estimated_costs),
            "total": round(sum(estimated_costs), 8) if estimated_costs else None,
            "mean_per_covered_case": round(statistics.fmean(estimated_costs), 8) if estimated_costs else None,
        },
        "llm_stage_totals": {
            stage: {
                name: round(value, 2) if name == "latency_ms" else int(value)
                for name, value in values.items()
            }
            for stage, values in sorted(llm_stage_totals.items())
        },
        "hard_gate_failures": dict(failure_counts),
        "run_status_counts": dict(run_status_counts),
    }


def write_results(
    experiment_dir: Path,
    scores: list[ScoredCase],
    *,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    score_dir = experiment_dir / "scores"
    for score in scores:
        write_json(score_dir / f"{score.case_id}.json", score.to_dict())

    summary = aggregate_scores(
        scores,
        bootstrap_config=(config or {}).get("bootstrap"),
    )
    write_json(experiment_dir / "summary.json", summary)
    _write_csv(experiment_dir / "results.csv", scores)
    (experiment_dir / "report.md").write_text(
        render_markdown(summary, scores),
        encoding="utf-8",
        newline="\n",
    )
    return summary


def _write_csv(path: Path, scores: list[ScoredCase]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    metric_names = sorted({name for score in scores for name in score.metrics})
    fieldnames = [
        "case_id", "category", "quality_score", "gate_passed", "end_to_end_latency_ms",
        "llm_call_count", "total_tokens", "estimated_cost", "tool_evidence_round_count", "backfill_count", "hard_gate_failures",
        *metric_names,
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for score in scores:
            row = {
                "case_id": score.case_id,
                "category": score.category,
                "quality_score": score.quality_score,
                "gate_passed": score.gate_passed,
                "end_to_end_latency_ms": score.runtime.get("end_to_end_latency_ms"),
                "llm_call_count": score.runtime.get("llm_call_count"),
                "total_tokens": score.runtime.get("total_tokens"),
                "estimated_cost": score.runtime.get("estimated_cost"),
                "tool_evidence_round_count": score.runtime.get("tool_evidence_round_count"),
                "backfill_count": score.runtime.get("backfill_count"),
                "hard_gate_failures": ";".join(score.hard_gate_failures),
            }
            row.update({name: score.metrics[name]["score"] for name in metric_names})
            writer.writerow(row)


def render_markdown(summary: dict[str, Any], scores: list[ScoredCase]) -> str:
    lines = [
        "# FinancialAnalyst 第二迭代评测报告",
        "",
        "> 使用真实 PostgreSQL、TuShare 回源和真实 LLM。主链路分数来自确定性规则；Reflection 缺陷集单独评测。",
        "",
        "## 总览",
        "",
        "| 指标 | 结果 |",
        "| --- | ---: |",
        f"| 用例数 | {summary.get('case_count')} |",
        f"| 端到端综合均分（失败计 0） | {_display(summary.get('quality_score_mean'))} |",
        f"| 综合均分 95% CI | {_ci_display(summary.get('quality_score_confidence_interval'))} |",
        f"| 重复运行题内标准差 | {_display(summary.get('repeat_stability', {}).get('mean_within_case_stddev'))} |",
        f"| 成功交付报告的内容均分 | {_display(summary.get('delivered_quality_score_mean'))} |",
        f"| 工作流成功交付率 | {_display(summary.get('workflow_success_rate'), '%')} |",
        f"| 硬门槛通过率 | {_display(summary.get('gate_pass_rate'), '%')} |",
        f"| 成功形成运行结果 | {summary.get('run_status_counts', {}).get('completed', 0)} |",
        f"| 超时用例 | {summary.get('run_status_counts', {}).get('timed_out', 0)} |",
        f"| 端到端延迟 P50 | {_display(summary.get('latency_ms', {}).get('p50'), ' ms')} |",
        f"| 端到端延迟 P95 | {_display(summary.get('latency_ms', {}).get('p95'), ' ms')} |",
        f"| Token 覆盖率 | {_display(summary.get('token_usage', {}).get('coverage_rate'), '%')} |",
        f"| Token 总量 | {_display(summary.get('token_usage', {}).get('total'))} |",
        f"| 估算成本合计 | {_display(summary.get('estimated_cost', {}).get('total'))} |",
        "",
        "## 分项得分",
        "",
        "| 评分项 | 平均分 |",
        "| --- | ---: |",
    ]
    for name, value in summary.get("metric_means", {}).items():
        lines.append(f"| {name} | {value:.2f} |")

    lines.extend(
        [
            "",
            "## 成功交付用例的分项得分",
            "",
            "| 评分项 | 平均分 |",
            "| --- | ---: |",
        ]
    )
    for name, value in summary.get("delivered_metric_means", {}).items():
        lines.append(f"| {name} | {value:.2f} |")

    lines.extend(
        [
            "",
            "## 单用例结果",
            "",
            "| Case | 类别 | 总分 | 门槛 | 延迟 |",
            "| --- | --- | ---: | :---: | ---: |",
        ]
    )
    for score in scores:
        latency = score.runtime.get("end_to_end_latency_ms")
        lines.append(
            f"| {score.case_id} | {score.category} | {score.quality_score:.2f} | "
            f"{'通过' if score.gate_passed else '未通过'} | {_display(latency, ' ms')} |"
        )

    lines.extend(
        [
            "",
            "## 口径说明",
            "",
            "- `fact_grounding` 只核对结构化 supporting metrics 与 Analysis evidence，不抽取报告自由文本中的全部事实。",
            "- `data_completeness` 以系统本次规划要求的数据分片与报告期完整性结果为依据。",
            "- Token 仅统计 provider usage；成本只在配置实际服务单价后计算，不使用猜测价格。",
            "- TuShare 历史数据稳定，但本报告仍保存每条用例的完整运行 state，便于复核与后续 replay。",
            "",
        ]
    )
    return "\n".join(lines)


def _display(value: Any, suffix: str = "") -> str:
    if value is None:
        return "--"
    if isinstance(value, float):
        return f"{value:.2f}{suffix}"
    return f"{value}{suffix}"


def _ci_display(value: Any) -> str:
    if not isinstance(value, dict) or value.get("lower") is None:
        return "--"
    return f"[{value['lower']:.2f}, {value['upper']:.2f}]"
