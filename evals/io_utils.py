"""评测文件的安全读写辅助函数。"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Iterable

from evals.models import EvalCase


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SUITE_PATH = PROJECT_ROOT / "evals" / "datasets" / "benchmark_v2_cases.jsonl"
DEFAULT_OUTPUT_ROOT = PROJECT_ROOT / "outputs" / "evals"


def load_cases(path: Path) -> list[EvalCase]:
    """读取 JSONL 测试集并进行基础唯一性校验。"""
    cases: list[EvalCase] = []
    seen_ids: set[str] = set()
    with path.open("r", encoding="utf-8") as handle:
        for line_number, raw_line in enumerate(handle, start=1):
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_number} 不是合法 JSON: {exc}") from exc
            case = EvalCase.from_dict(payload)
            if case.case_id in seen_ids:
                raise ValueError(f"重复 case_id: {case.case_id}")
            if not case.query.strip():
                raise ValueError(f"{case.case_id} 的 query 为空")
            seen_ids.add(case.case_id)
            cases.append(case)
    if not cases:
        raise ValueError(f"测试集为空: {path}")
    return cases


def write_json(path: Path, payload: Any) -> None:
    """先写临时文件再替换，避免中断后留下半个 JSON。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2, default=str)
        handle.write("\n")
    os.replace(temporary, path)


def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def select_cases(
    cases: Iterable[EvalCase],
    *,
    case_ids: set[str] | None = None,
    limit: int | None = None,
) -> list[EvalCase]:
    selected = [case for case in cases if not case_ids or case.case_id in case_ids]
    if case_ids:
        missing = case_ids - {case.case_id for case in selected}
        if missing:
            raise ValueError(f"测试集中不存在 case_id: {sorted(missing)}")
    if limit is not None:
        if limit <= 0:
            raise ValueError("limit 必须大于 0")
        selected = selected[:limit]
    return selected
