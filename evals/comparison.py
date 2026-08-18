"""两个实验目录的同 case 成对对照分析。"""

from __future__ import annotations

import statistics
from pathlib import Path
from typing import Any

from evals.io_utils import read_json, write_json
from evals.statistics import bootstrap_mean_ci


def compare_experiments(
    baseline_dir: Path,
    candidate_dir: Path,
    *,
    bootstrap_config: dict[str, Any] | None = None,
    output_path: Path | None = None,
) -> dict[str, Any]:
    baseline = _load_scores(baseline_dir)
    candidate = _load_scores(candidate_dir)
    paired_ids = sorted(set(baseline) & set(candidate))
    if not paired_ids:
        raise ValueError("两个实验没有可成对比较的 case_id")
    boot = dict(bootstrap_config or {})
    kwargs = {
        "samples": int(boot.get("samples", 5000)),
        "confidence_level": float(boot.get("confidence_level", 0.95)),
        "seed": int(boot.get("seed", 20260813)),
    }

    quality_deltas = [
        float(candidate[case_id].get("quality_score") or 0)
        - float(baseline[case_id].get("quality_score") or 0)
        for case_id in paired_ids
    ]
    runtime_metrics = (
        "end_to_end_latency_ms", "llm_latency_ms", "total_tokens", "estimated_cost"
    )
    runtime_deltas: dict[str, Any] = {}
    for name in runtime_metrics:
        values = _paired_runtime_delta(baseline, candidate, paired_ids, name)
        runtime_deltas[name] = bootstrap_mean_ci(values, **kwargs) if values else None

    metric_names = sorted(
        set.intersection(*[
            set((baseline[case_id].get("metrics") or {}).keys())
            & set((candidate[case_id].get("metrics") or {}).keys())
            for case_id in paired_ids
        ])
    ) if paired_ids else []
    metric_deltas = {}
    for name in metric_names:
        values = [
            float(candidate[case_id]["metrics"][name]["score"])
            - float(baseline[case_id]["metrics"][name]["score"])
            for case_id in paired_ids
        ]
        metric_deltas[name] = bootstrap_mean_ci(values, **kwargs)

    result = {
        "schema_version": 2,
        "baseline_dir": str(baseline_dir.resolve()),
        "candidate_dir": str(candidate_dir.resolve()),
        "paired_case_count": len(paired_ids),
        "paired_case_ids": paired_ids,
        "quality_score_delta": bootstrap_mean_ci(quality_deltas, **kwargs),
        "candidate_win_rate": round(
            100 * sum(delta > 0 for delta in quality_deltas) / len(quality_deltas), 2
        ),
        "candidate_tie_rate": round(
            100 * sum(delta == 0 for delta in quality_deltas) / len(quality_deltas), 2
        ),
        "metric_score_deltas": metric_deltas,
        "runtime_deltas": runtime_deltas,
    }
    if output_path:
        write_json(output_path, result)
        output_path.with_suffix(".md").write_text(_render_markdown(result), encoding="utf-8")
    return result


def _load_scores(experiment_dir: Path) -> dict[str, dict[str, Any]]:
    score_dir = experiment_dir / "scores"
    result = {}
    for path in sorted(score_dir.glob("*.json")):
        payload = read_json(path)
        case_id = str(payload.get("case_id") or path.stem)
        result[case_id] = payload
    if not result:
        raise ValueError(f"没有找到评分产物: {score_dir}")
    return result


def _paired_runtime_delta(
    baseline: dict[str, dict[str, Any]],
    candidate: dict[str, dict[str, Any]],
    case_ids: list[str],
    name: str,
) -> list[float]:
    values = []
    for case_id in case_ids:
        old = (baseline[case_id].get("runtime") or {}).get(name)
        new = (candidate[case_id].get("runtime") or {}).get(name)
        if isinstance(old, (int, float)) and isinstance(new, (int, float)):
            values.append(float(new) - float(old))
    return values


def _render_markdown(result: dict[str, Any]) -> str:
    quality = result["quality_score_delta"]
    lines = [
        "# FinancialAnalyst 成对实验对比",
        "",
        f"- 成对用例数：{result['paired_case_count']}",
        f"- 质量分平均变化：{quality['mean']:.2f}",
        f"- 质量分 95% CI：[{quality['lower']:.2f}, {quality['upper']:.2f}]",
        f"- Candidate 胜率：{result['candidate_win_rate']:.2f}%",
        "",
        "正数表示 Candidate 高于 Baseline；延迟、Token 和成本通常以负数为改善。",
        "",
    ]
    return "\n".join(lines)
