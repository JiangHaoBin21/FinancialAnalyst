"""第二迭代评测命令行入口。"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from evals.io_utils import (
    DEFAULT_OUTPUT_ROOT,
    DEFAULT_SUITE_PATH,
    load_cases,
    read_json,
    select_cases,
    write_json,
)
from evals.models import ScoredCase
from evals.models import EvalCase
from evals.comparison import compare_experiments
from evals.reporting import write_results
from evals.reflection_mutations import (
    aggregate_reflection_results,
    build_mutation_dataset,
    run_reflection_input,
)
from evals.runner import create_manifest, run_case_isolated, run_preflight
from evals.scorers import score_case


DEFAULT_CONFIG = Path(__file__).resolve().parent / "config" / "v2.json"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="FinancialAnalyst 第二迭代评测系统")
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate = subparsers.add_parser("validate", help="校验测试集和配置，不调用外部服务")
    _add_common_inputs(validate)

    preflight = subparsers.add_parser("preflight", help="检查配置和 PostgreSQL 连通性，不调用 LLM/TuShare")
    _add_common_inputs(preflight)

    run = subparsers.add_parser("run", help="使用真实数据库、TuShare 与 LLM 执行并评分")
    _add_common_inputs(run)
    run.add_argument("--experiment-id", help="自定义实验 ID")
    run.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    run.add_argument("--case-id", action="append", dest="case_ids", help="只运行指定 case，可重复传入")
    run.add_argument("--limit", type=int, help="只运行测试集前 N 条")
    run.add_argument("--repeat", type=int, default=1, help="每条用例重复执行次数，默认 1")
    run.add_argument("--rerun", action="store_true", help="覆盖已存在的单例原始产物")
    run.add_argument(
        "--variant",
        choices=("full", "no_reflection"),
        default="full",
        help="full 为完整工作流；no_reflection 为 Reflection LLM 消融变体",
    )
    run.add_argument(
        "--case-timeout-seconds",
        type=float,
        default=600.0,
        help="单条用例最大运行时间，默认 600 秒",
    )

    score = subparsers.add_parser("score", help="对已有 raw 产物重新评分，不调用外部服务")
    _add_common_inputs(score)
    score.add_argument("--experiment-dir", type=Path, required=True)
    score.add_argument(
        "--output-dir",
        type=Path,
        help="将重评分结果写入新目录；推荐使用，以保持源实验不可变",
    )
    score.add_argument("--case-id", action="append", dest="case_ids")

    compare = subparsers.add_parser("compare", help="对两个已有实验做同 case 成对比较")
    _add_common_inputs(compare)
    compare.add_argument("--baseline-dir", type=Path, required=True)
    compare.add_argument("--candidate-dir", type=Path, required=True)
    compare.add_argument("--output", type=Path, required=True)

    reflection_build = subparsers.add_parser(
        "reflection-build", help="从成功报告构建 Reflection 缺陷注入集，不调用 LLM"
    )
    _add_common_inputs(reflection_build)
    reflection_build.add_argument("--source-experiment-dir", type=Path, required=True)
    reflection_build.add_argument("--output-dir", type=Path, required=True)
    reflection_build.add_argument(
        "--matrix",
        type=Path,
        default=Path(__file__).resolve().parent / "config" / "reflection_mutations.json",
    )

    reflection_run = subparsers.add_parser(
        "reflection-run", help="只运行 ReflectionAgent 缺陷检测实验"
    )
    _add_common_inputs(reflection_run)
    reflection_run.add_argument("--experiment-dir", type=Path, required=True)
    reflection_run.add_argument("--limit", type=int)
    reflection_run.add_argument("--rerun", action="store_true")

    reflection_score = subparsers.add_parser(
        "reflection-score", help="汇总已有 Reflection 缺陷检测产物"
    )
    _add_common_inputs(reflection_score)
    reflection_score.add_argument("--experiment-dir", type=Path, required=True)
    return parser


def _add_common_inputs(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--suite", type=Path, default=DEFAULT_SUITE_PATH)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    try:
        config = read_json(args.config)
        cases = load_cases(args.suite)
        _validate_config(config)
        _validate_suite(
            cases,
            config,
            enforce_expected_count=args.suite.resolve() == DEFAULT_SUITE_PATH.resolve(),
        )
        if args.command == "validate":
            category_counts = {
                category: sum(case.category == category for case in cases)
                for category in sorted({case.category for case in cases})
            }
            print(json.dumps(
                {"valid": True, "case_count": len(cases), "category_counts": category_counts},
                ensure_ascii=False,
                indent=2,
            ))
            return
        if args.command == "preflight":
            result = run_preflight()
            print(json.dumps(result, ensure_ascii=False, indent=2))
            if not result["ready"]:
                raise SystemExit(2)
            return
        if args.command == "run":
            selected = select_cases(
                cases,
                case_ids=set(args.case_ids) if args.case_ids else None,
                limit=args.limit,
            )
            selected = _expand_repeats(selected, args.repeat)
            experiment_id = args.experiment_id or datetime.now().strftime("pilot-%Y%m%d-%H%M%S")
            experiment_dir = args.output_root.resolve() / experiment_id
            experiment_dir.mkdir(parents=True, exist_ok=True)
            pricing = dict(config.get("model_pricing") or {})
            manifest = create_manifest(
                experiment_id,
                selected,
                suite_path=args.suite,
                pricing=pricing,
                variant=args.variant,
            )
            preflight_result = run_preflight()
            manifest["preflight"] = preflight_result
            write_json(experiment_dir / "manifest.json", manifest)
            if not preflight_result["ready"]:
                raise RuntimeError(
                    "运行环境预检未通过；请先执行 `python -m evals preflight` 查看详情，"
                    "修复后使用同一 experiment-id 继续。"
                )
            scores: list[ScoredCase] = []
            for index, case in enumerate(selected, start=1):
                print(f"[{index}/{len(selected)}] 运行 {case.case_id}: {case.query}", flush=True)
                run_payload = run_case_isolated(
                    experiment_dir,
                    case,
                    rerun=args.rerun,
                    timeout_seconds=args.case_timeout_seconds,
                    pricing=pricing,
                    variant=args.variant,
                )
                scored = score_case(case, run_payload, config=config)
                scores.append(scored)
                print(
                    f"[{case.case_id}] run={run_payload.get('run_status')} "
                    f"score={scored.quality_score:.2f} gate={'PASS' if scored.gate_passed else 'FAIL'}",
                    flush=True,
                )
            summary = write_results(experiment_dir, scores, config=config)
            print(json.dumps({"experiment_dir": str(experiment_dir), "summary": summary}, ensure_ascii=False, indent=2))
            return
        if args.command == "score":
            scores = []
            requested = set(args.case_ids) if args.case_ids else None
            oracle_by_id = {case.case_id: case for case in cases}
            for raw_path in sorted((args.experiment_dir / "raw").glob("*.json")):
                raw_payload = read_json(raw_path)
                raw_case = EvalCase.from_dict(raw_payload.get("case") or {})
                source_case_id = raw_case.source_case_id or raw_case.case_id
                oracle = oracle_by_id.get(source_case_id)
                if oracle is None:
                    continue
                selectable_ids = {raw_case.case_id, source_case_id}
                if requested and not requested.intersection(identifier for identifier in selectable_ids if identifier):
                    continue
                case_payload = oracle.to_dict()
                case_payload.update(
                    {
                        "case_id": raw_case.case_id,
                        "source_case_id": source_case_id,
                        "repeat_index": raw_case.repeat_index,
                    }
                )
                case = EvalCase.from_dict(case_payload)
                scores.append(score_case(case, raw_payload, config=config))
            if not scores:
                raise ValueError(f"没有找到可评分 raw 产物: {args.experiment_dir / 'raw'}")
            output_dir = args.output_dir or args.experiment_dir
            output_dir.mkdir(parents=True, exist_ok=True)
            if args.output_dir:
                write_json(
                    output_dir / "manifest.json",
                    {
                        "schema_version": 2,
                        "experiment_type": "rescore",
                        "source_experiment_dir": str(args.experiment_dir.resolve()),
                        "suite_path": str(args.suite.resolve()),
                        "config_path": str(args.config.resolve()),
                        "case_ids": [score.case_id for score in scores],
                    },
                )
            summary = write_results(output_dir, scores, config=config)
            print(json.dumps(
                {
                    "source_experiment_dir": str(args.experiment_dir),
                    "output_dir": str(output_dir),
                    "summary": summary,
                },
                ensure_ascii=False,
                indent=2,
            ))
            return
        if args.command == "compare":
            result = compare_experiments(
                args.baseline_dir,
                args.candidate_dir,
                bootstrap_config=config.get("bootstrap"),
                output_path=args.output,
            )
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return
        if args.command == "reflection-build":
            manifest = build_mutation_dataset(
                args.source_experiment_dir,
                args.output_dir,
                read_json(args.matrix),
            )
            print(json.dumps(manifest, ensure_ascii=False, indent=2))
            return
        if args.command == "reflection-run":
            input_paths = sorted((args.experiment_dir / "inputs").glob("*.json"))
            if args.limit is not None:
                if args.limit <= 0:
                    raise ValueError("limit 必须大于 0")
                input_paths = input_paths[:args.limit]
            if not input_paths:
                raise ValueError(f"没有 Reflection 输入: {args.experiment_dir / 'inputs'}")
            for index, input_path in enumerate(input_paths, start=1):
                print(f"[{index}/{len(input_paths)}] Reflection {input_path.stem}", flush=True)
                result = run_reflection_input(
                    input_path,
                    args.experiment_dir,
                    pricing=config.get("model_pricing"),
                    rerun=args.rerun,
                )
                print(
                    f"[{input_path.stem}] run={result['run_status']} "
                    f"score={result['score']['score']:.2f} "
                    f"耗时={result['runtime']['end_to_end_latency_ms'] / 1000:.3f}秒",
                    flush=True,
                )
            summary = aggregate_reflection_results(args.experiment_dir)
            print(json.dumps(summary, ensure_ascii=False, indent=2))
            return
        if args.command == "reflection-score":
            summary = aggregate_reflection_results(args.experiment_dir)
            print(json.dumps(summary, ensure_ascii=False, indent=2))
            return
    except Exception as exc:
        print(f"评测失败: {type(exc).__name__}: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc


def _validate_config(config: dict[str, Any]) -> None:
    weights = config.get("quality_weights") or {}
    if not weights:
        raise ValueError("配置缺少 quality_weights")
    if abs(sum(float(value) for value in weights.values()) - 1.0) > 1e-9:
        raise ValueError("quality_weights 权重之和必须为 1")
    for name, value in (config.get("model_pricing") or {}).items():
        if name.endswith("_per_million_tokens") and value is not None:
            if not isinstance(value, (int, float)) or value < 0:
                raise ValueError(f"{name} 必须是非负数或 null")


def _validate_suite(
    cases: list[Any],
    config: dict[str, Any],
    *,
    enforce_expected_count: bool = False,
) -> None:
    expected_count = config.get("benchmark_expected_case_count")
    if enforce_expected_count and expected_count is not None and len(cases) != int(expected_count):
        raise ValueError(f"第二迭代基准集必须为 {expected_count} 条，实际为 {len(cases)} 条")
    if enforce_expected_count:
        actual_categories = {
            category: sum(case.category == category for case in cases)
            for category in {case.category for case in cases}
        }
        expected_categories = config.get("benchmark_expected_categories") or {}
        if actual_categories != expected_categories:
            raise ValueError(
                f"第二迭代类别分布不符合配置：expected={expected_categories}, actual={actual_categories}"
            )
    for case in cases:
        expected = case.expected
        if not expected.get("outcomes"):
            raise ValueError(f"{case.case_id} 缺少 expected.outcomes")
        if expected.get("deliverable_required", True):
            if not expected.get("required_dimensions"):
                raise ValueError(f"{case.case_id} 缺少 required_dimensions")
            if not expected.get("required_data_parts"):
                raise ValueError(f"{case.case_id} 缺少 required_data_parts")


def _expand_repeats(cases: list[EvalCase], repeat: int) -> list[EvalCase]:
    if repeat <= 0:
        raise ValueError("repeat 必须大于 0")
    if repeat == 1:
        return cases
    expanded = []
    for case in cases:
        for index in range(1, repeat + 1):
            payload = case.to_dict()
            payload["source_case_id"] = case.source_case_id or case.case_id
            payload["case_id"] = f"{case.case_id}__r{index}"
            payload["repeat_index"] = index
            expanded.append(EvalCase.from_dict(payload))
    return expanded


if __name__ == "__main__":
    main()
