from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from evals.comparison import compare_experiments
from evals.io_utils import load_cases, read_json, write_json
from evals.reflection_mutations import (
    apply_mutation,
    expand_mutation_matrix,
    score_reflection_result,
)
from evals.scorers.limitations import classify_limitations
from evals.statistics import bootstrap_mean_ci
from evals.telemetry import TimedLLMProxy
from evals.cli import _expand_repeats
from evals.models import EvalCase
from evals.variants import NoOpReflectionAgent


class _UsageClient:
    def __init__(self) -> None:
        self.last_usage = {}

    def generate(self, messages, tools=None, **kwargs):
        self.last_usage = {
            "model": "test-model",
            "prompt_tokens": 100,
            "cached_prompt_tokens": 20,
            "completion_tokens": 40,
            "reasoning_tokens": 10,
            "total_tokens": 140,
        }
        return SimpleNamespace(tool_calls=[])


class V2EvaluationTests(unittest.TestCase):
    def test_default_v2_suite_has_30_unique_cases_and_required_categories(self) -> None:
        path = Path(__file__).resolve().parents[1] / "datasets" / "benchmark_v2_cases.jsonl"
        cases = load_cases(path)
        self.assertEqual(len(cases), 30)
        self.assertEqual(len({case.case_id for case in cases}), 30)
        categories = {case.category for case in cases}
        self.assertTrue(
            {
                "single_dimension", "comprehensive_analysis", "multi_year_trend",
                "investment_boundary", "risk_analysis", "backfill_candidate",
                "clarification", "exception_recovery",
            }.issubset(categories)
        )

    def test_telemetry_aggregates_provider_tokens_and_configured_cost(self) -> None:
        proxy = TimedLLMProxy(
            _UsageClient(),
            pricing={
                "currency": "CNY",
                "input_per_million_tokens": 2.0,
                "cached_input_per_million_tokens": 0.5,
                "output_per_million_tokens": 8.0,
            },
        )
        proxy.generate(messages=[{"role": "user", "content": "x"}])
        snapshot = proxy.snapshot()
        self.assertTrue(snapshot["token_usage_available"])
        self.assertEqual(snapshot["total_tokens"], 140)
        self.assertEqual(snapshot["reasoning_tokens"], 10)
        self.assertAlmostEqual(snapshot["estimated_cost"], 0.00049)

    def test_telemetry_attributes_calls_to_agent_stage(self) -> None:
        proxy = TimedLLMProxy(_UsageClient())
        proxy.generate(
            messages=[
                {"role": "system", "content": "你是 ReflectionAgent，负责最终质量审查。"},
                {"role": "user", "content": "review"},
            ]
        )
        snapshot = proxy.snapshot()
        self.assertEqual(snapshot["llm_calls"][0]["stage"], "reflection")
        self.assertEqual(snapshot["llm_stage_usage"]["reflection"]["total_tokens"], 140)

    def test_limitation_semantics_survive_paraphrase(self) -> None:
        source = classify_limitations(["缺少同行可比公司的横向比较"])
        target = classify_limitations(["当前未纳入行业对比数据"])
        self.assertEqual(source, {"missing_peer_benchmark"})
        self.assertEqual(target, source)

    def test_mutation_matrix_expands_to_50_and_injects_single_fault(self) -> None:
        matrix = read_json(
            Path(__file__).resolve().parents[1] / "config" / "reflection_mutations.json"
        )
        specs = expand_mutation_matrix(matrix)
        self.assertEqual(len(specs), 50)
        state = {
            "analysis_result": {"data_limitations": ["缺少行业对比"]},
            "report_result": {
                "title": "示例公司报告",
                "conclusion": "结论",
                "sections": [{"heading": "盈利能力", "summary": "稳定"}],
                "data_limitations": ["缺少行业对比"],
                "markdown_report": "# 示例公司报告\n\n## 盈利能力\n稳定\n\n## 数据限制\n缺少行业对比",
            },
        }
        mutated = apply_mutation(state, "unsupported_claim")
        self.assertIn("未来三年锁定订单", mutated["report_result"]["markdown_report"])
        self.assertEqual(mutated["analysis_result"], state["analysis_result"])

    def test_reflection_score_checks_issue_decision_and_route(self) -> None:
        spec = {
            "mutation_id": "x",
            "type": "unsupported_claim",
            "expected_issue_types": ["unsupported_claim"],
            "acceptable_decisions": ["needs_report_regeneration"],
            "expected_route": "report",
        }
        score = score_reflection_result(
            spec,
            {
                "decision": "needs_report_regeneration",
                "recommended_next_stage": "report",
                "issues": [{"type": "unsupported_claim"}],
            },
        )
        self.assertEqual(score["score"], 100.0)
        self.assertEqual(score["issue_recall"], 1.0)

    def test_bootstrap_is_reproducible(self) -> None:
        first = bootstrap_mean_ci([1.0, 2.0, 3.0], samples=500, seed=7)
        second = bootstrap_mean_ci([1.0, 2.0, 3.0], samples=500, seed=7)
        self.assertEqual(first, second)
        self.assertEqual(first["mean"], 2.0)

    def test_paired_comparison_reports_candidate_delta(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            baseline = root / "baseline"
            candidate = root / "candidate"
            for target, quality, latency in ((baseline, 80.0, 1000), (candidate, 90.0, 800)):
                write_json(
                    target / "scores" / "case.json",
                    {
                        "case_id": "case",
                        "quality_score": quality,
                        "metrics": {"safety": {"score": quality}},
                        "runtime": {"end_to_end_latency_ms": latency},
                    },
                )
            result = compare_experiments(
                baseline,
                candidate,
                bootstrap_config={"samples": 100, "seed": 1},
            )
            self.assertEqual(result["quality_score_delta"]["mean"], 10.0)
            self.assertEqual(result["runtime_deltas"]["end_to_end_latency_ms"]["mean"], -200.0)

    def test_repeat_expansion_produces_stable_run_ids(self) -> None:
        case = EvalCase(case_id="case", category="x", query="q")
        repeated = _expand_repeats([case], 3)
        self.assertEqual([item.case_id for item in repeated], ["case__r1", "case__r2", "case__r3"])
        self.assertEqual({item.source_case_id for item in repeated}, {"case"})

    def test_no_reflection_variant_is_deterministic_and_routes_to_finished(self) -> None:
        result = NoOpReflectionAgent().run({})
        self.assertEqual(result["decision"], "pass")
        self.assertEqual(result["recommended_next_stage"], "finished")


if __name__ == "__main__":
    unittest.main()
