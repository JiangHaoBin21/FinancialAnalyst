"""真实数据库、TuShare 与 LLM 的第二迭代批量执行器。"""

from __future__ import annotations

import platform
import subprocess
import sys
import traceback
from multiprocessing import get_context
from datetime import datetime
from pathlib import Path
from time import perf_counter
from typing import Any
from uuid import uuid4

from evals.io_utils import PROJECT_ROOT, read_json, write_json
from evals.models import EvalCase
from evals.telemetry import TimedLLMProxy
from evals.variants import apply_workflow_variant


def git_revision() -> str | None:
    try:
        completed = subprocess.run(
            ["git", "-c", f"safe.directory={PROJECT_ROOT.as_posix()}", "rev-parse", "HEAD"],
            cwd=PROJECT_ROOT,
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return completed.stdout.strip() or None


def create_manifest(
    experiment_id: str,
    cases: list[EvalCase],
    *,
    suite_path: Path | None = None,
    pricing: dict[str, Any] | None = None,
    variant: str = "full",
) -> dict[str, Any]:
    from app.core.config import settings

    return {
        "schema_version": 2,
        "experiment_id": experiment_id,
        "created_at": datetime.now().astimezone().isoformat(),
        "mode": "live",
        "variant": variant,
        "data_policy": "本地 PostgreSQL 优先，缺失时允许 TuShare 回源；每次完整 state 均保存用于复核。",
        "case_ids": [case.case_id for case in cases],
        "case_count": len(cases),
        "category_counts": {
            category: sum(case.category == category for case in cases)
            for category in sorted({case.category for case in cases})
        },
        "suite_path": str(suite_path.resolve()) if suite_path else None,
        "git_revision": git_revision(),
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "model": settings.deepseek_model_name,
        "model_pricing": dict(pricing or {}),
        "base_url_host_recorded": False,
        "secrets_recorded": False,
    }


def run_preflight() -> dict[str, Any]:
    """在产生外部调用费用前验证关键配置和 PostgreSQL 可达性。"""
    from sqlalchemy import text

    from app.core.config import settings
    from app.core.database import engine

    checks = {
        "database_configured": bool(settings.database_url),
        "tushare_configured": bool(settings.TuShare_Token),
        "llm_key_configured": bool(settings.deepseek_api_key),
        "model_configured": bool(settings.deepseek_model_name),
        "database_reachable": False,
    }
    error: dict[str, str] | None = None
    if all(checks[name] for name in checks if name != "database_reachable"):
        try:
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            checks["database_reachable"] = True
        except Exception as exc:
            error = {"type": type(exc).__name__, "message": str(exc)}

    return {
        "ready": all(checks.values()),
        "checks": checks,
        "error": error,
        "note": "预检不调用 LLM 或 TuShare API；只检查配置存在性和 PostgreSQL 连通性。",
    }


class LiveEvalRunner:
    """通过应用层 Runner 执行用例，单条失败不会终止批次。"""

    def __init__(
        self,
        experiment_dir: Path,
        pricing: dict[str, Any] | None = None,
        variant: str = "full",
    ):
        self.experiment_dir = experiment_dir
        self.raw_dir = experiment_dir / "raw"
        self._runner: Any | None = None
        self._telemetry: TimedLLMProxy | None = None
        self.pricing = dict(pricing or {})
        self.variant = variant

    def _ensure_runner(self) -> None:
        if self._runner is not None:
            return
        from app.application.financial_analysis_runner import FinancialAnalysisRunner
        from app.llms.openai_client import OpenAIClient

        self._telemetry = TimedLLMProxy(OpenAIClient(), pricing=self.pricing)
        # 当前基准不评测断点恢复；关闭 checkpoint，避免把可选 checkpoint
        # 驱动的安装状态误计为财务分析质量。业务 API 的默认配置不受影响。
        self._runner = FinancialAnalysisRunner(
            llm_client=self._telemetry,
            enable_postgres_checkpoint=False,
        )
        apply_workflow_variant(self._runner.workflow_graph, self.variant)

    def run_case(self, case: EvalCase, *, rerun: bool = False) -> dict[str, Any]:
        output_path = self.raw_dir / f"{case.case_id}.json"
        if output_path.exists() and not rerun:
            return read_json(output_path)

        started_at = datetime.now().astimezone()
        started_clock = perf_counter()
        payload: dict[str, Any]
        try:
            self._ensure_runner()
            assert self._telemetry is not None
            self._telemetry.reset()
            thread_id = f"eval-{case.case_id}-{uuid4().hex[:12]}"
            result = self._runner.run(case.query, thread_id=thread_id)
            state = result.to_dict(include_state=True).get("state") or {}
            runtime = self._telemetry.snapshot()
            runtime.update(
                {
                    "thread_id": thread_id,
                    "started_at": started_at.isoformat(),
                    "finished_at": datetime.now().astimezone().isoformat(),
                    "end_to_end_latency_ms": round((perf_counter() - started_clock) * 1000, 2),
                    "tool_evidence_round_count": _evidence_round_count(state),
                    "stage_attempt_counts": state.get("stage_attempt_counts") or {},
                    "backfill_count": int(state.get("already_backfill") or 0),
                }
            )
            payload = {
                "schema_version": 1,
                "case": case.to_dict(),
                "run_status": "completed",
                "state": state,
                "runtime": runtime,
            }
        except Exception as exc:
            telemetry = self._telemetry.snapshot() if self._telemetry else {}
            telemetry.update(
                {
                    "started_at": started_at.isoformat(),
                    "finished_at": datetime.now().astimezone().isoformat(),
                    "end_to_end_latency_ms": round((perf_counter() - started_clock) * 1000, 2),
                }
            )
            message = f"{type(exc).__name__}: {exc}"
            payload = {
                "schema_version": 1,
                "case": case.to_dict(),
                "run_status": "failed",
                "state": {
                    "status": "error",
                    "current_stage": "error",
                    "has_error": True,
                    "error_message": message,
                    "analysis_result": {},
                    "report_result": {},
                    "execution_history": [],
                },
                "runtime": telemetry,
                "exception": {
                    "type": type(exc).__name__,
                    "message": str(exc),
                    "traceback": "".join(traceback.format_exception(exc)),
                },
            }

        write_json(output_path, payload)
        return payload

    def close(self) -> None:
        if self._runner is not None:
            self._runner.close()


def _evidence_round_count(state: dict[str, Any]) -> int:
    import json

    value = (state.get("analysis_result") or {}).get("evidence")
    if not isinstance(value, str):
        return 0
    try:
        evidence = json.loads(value)
    except json.JSONDecodeError:
        return 0
    return len(evidence) if isinstance(evidence, list) else 0


def run_case_isolated(
    experiment_dir: Path,
    case: EvalCase,
    *,
    rerun: bool = False,
    timeout_seconds: float = 600.0,
    pricing: dict[str, Any] | None = None,
    variant: str = "full",
) -> dict[str, Any]:
    """在独立进程执行单例，使超时和崩溃不会阻断整个批次。"""
    output_path = experiment_dir / "raw" / f"{case.case_id}.json"
    if output_path.exists() and not rerun:
        return read_json(output_path)
    if timeout_seconds <= 0:
        raise ValueError("case timeout 必须大于 0")

    started_at = datetime.now().astimezone()
    context = get_context("spawn")
    process = context.Process(
        target=_run_case_worker,
        args=(str(experiment_dir), case.to_dict(), rerun, dict(pricing or {}), variant),
        name=f"eval-{case.case_id}",
    )
    process.start()
    process.join(timeout_seconds)

    if process.is_alive():
        process.terminate()
        process.join(10)
        payload = _terminated_payload(
            case,
            run_status="timed_out",
            error_type="EvaluationTimeout",
            message=f"用例执行超过 {timeout_seconds:g} 秒，评测进程已终止。",
            started_at=started_at,
            timeout_seconds=timeout_seconds,
        )
        write_json(output_path, payload)
        return payload

    if output_path.exists():
        return read_json(output_path)

    payload = _terminated_payload(
        case,
        run_status="crashed",
        error_type="EvaluationWorkerCrash",
        message=f"评测子进程退出且未生成产物，exit_code={process.exitcode}。",
        started_at=started_at,
    )
    write_json(output_path, payload)
    return payload


def _run_case_worker(
    experiment_dir: str,
    case_payload: dict[str, Any],
    rerun: bool,
    pricing: dict[str, Any],
    variant: str,
) -> None:
    runner = LiveEvalRunner(Path(experiment_dir), pricing=pricing, variant=variant)
    try:
        runner.run_case(EvalCase.from_dict(case_payload), rerun=rerun)
    finally:
        runner.close()
    # Windows 下 OpenAI/数据库客户端可能仍持有非守护后台资源，导致子进程在
    # 原始产物已经原子落盘后迟迟不退出。评测 worker 没有后续职责，此处显式
    # 结束进程，保证父批次能可靠进入下一条用例。
    import os

    os._exit(0)


def _terminated_payload(
    case: EvalCase,
    *,
    run_status: str,
    error_type: str,
    message: str,
    started_at: datetime,
    timeout_seconds: float | None = None,
) -> dict[str, Any]:
    finished_at = datetime.now().astimezone()
    return {
        "schema_version": 1,
        "case": case.to_dict(),
        "run_status": run_status,
        "state": {
            "status": "error",
            "current_stage": "error",
            "has_error": True,
            "error_message": message,
            "analysis_result": {},
            "report_result": {},
            "execution_history": [],
        },
        "runtime": {
            "started_at": started_at.isoformat(),
            "finished_at": finished_at.isoformat(),
            "end_to_end_latency_ms": round((finished_at - started_at).total_seconds() * 1000, 2),
            "case_timeout_seconds": timeout_seconds,
            "token_usage_available": False,
        },
        "exception": {"type": error_type, "message": message},
    }
