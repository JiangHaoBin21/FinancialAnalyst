# app/skills/planning/planning_parser.py

"""Planning parser: 负责将 planner 的原始文本输出解析为系统内部的 PlanningResult。"""

from __future__ import annotations

import json
import re
from typing import Any, Optional

from app.domain.models import PlanningResult, PlanningStep, TimeRange


ALLOWED_TASK_TYPES = {
    "financial_analysis",
    "financial_data_query",
    "unknown",
}

ALLOWED_OUTPUT_MODES = {
    "report",
    "summary",
}

ALLOWED_AGENTS = {
    "DataAgent",
    "AnalysisAgent",
    "ReportAgent",
    "ReflectionAgent",
}


def parse_planning_result(raw_response: str) -> Optional[PlanningResult]:
    """
    主入口：
    将 LLM 原始输出解析为 PlanningResult。

    返回值语义：
    - 成功解析并通过结构校验：返回 PlanningResult
    - 无法解析 / 结构不合法：返回 None

    注意：
    - 这里只做“解析 + 结构校验 + 类型转换”
    - 不做 fallback
    - 不做默认 plan 补全
    - 不做规则兜底提取
    - 不做 supervisor 层面的业务接受判断
    """
    data = parse_json_response(raw_response)
    if data is None:
        return None

    task_type = clean_optional_str(data.get("task_type")) or "unknown"
    if task_type not in ALLOWED_TASK_TYPES:
        return None

    company_name = clean_optional_str(data.get("company_name"))
    ts_code = normalize_ts_code(data.get("ts_code"))
    time_range = parse_time_range(data.get("time_range"))
    analysis_focus = clean_optional_str(data.get("analysis_focus"))

    output_mode = clean_optional_str(data.get("output_mode")) or "report"
    if output_mode not in ALLOWED_OUTPUT_MODES:
        output_mode = "report"

    planner_message = clean_optional_str(data.get("planner_message")) or ""

    needs_user_input = bool(data.get("needs_user_input", False))

    missing_fields_raw = data.get("missing_fields", [])
    if not isinstance(missing_fields_raw, list):
        return None
    missing_fields = [str(x).strip() for x in missing_fields_raw if str(x).strip()]

    task_plan_raw = data.get("task_plan", [])
    if not isinstance(task_plan_raw, list):
        return None

    task_plan = parse_task_plan(task_plan_raw)
    if task_plan is None:
        return None

    return PlanningResult(
        task_type=task_type,
        company_name=company_name,
        ts_code=ts_code,
        time_range=time_range,
        analysis_focus=analysis_focus,
        output_mode=output_mode,
        planner_message=planner_message,
        task_plan=task_plan,
        needs_user_input=needs_user_input,
        missing_fields=missing_fields,
        raw_response=raw_response,
    )


def parse_json_response(text: str) -> Optional[dict[str, Any]]:
    """
    尝试从模型输出中提取 JSON 对象。

    支持三种情况：
    1. 输出本身就是 JSON
    2. 输出被 ```json ... ``` 包裹
    3. 输出中夹杂其他文字，但包含第一个平衡的 JSON 对象
    """
    if not text or not text.strip():
        return None

    text = text.strip()

    # 1) 直接解析
    try:
        parsed = json.loads(text)
        return parsed if isinstance(parsed, dict) else None
    except json.JSONDecodeError:
        pass

    # 2) fenced code block
    fenced_match = re.search(
        r"```json\s*(.*?)\s*```",
        text,
        flags=re.DOTALL | re.IGNORECASE,
    )
    if fenced_match:
        fenced_text = fenced_match.group(1).strip()
        try:
            parsed = json.loads(fenced_text)
            return parsed if isinstance(parsed, dict) else None
        except json.JSONDecodeError:
            pass

    # 3) 文本中提取第一个平衡 JSON 对象
    candidate = extract_first_balanced_json_object(text)
    if candidate:
        try:
            parsed = json.loads(candidate)
            return parsed if isinstance(parsed, dict) else None
        except json.JSONDecodeError:
            return None

    return None


def extract_first_balanced_json_object(text: str) -> Optional[str]:
    """
    从文本中提取第一个括号平衡的 JSON 对象。
    比简单正则抓取更稳，能避免贪婪匹配导致的截断问题。
    """
    start = text.find("{")
    if start == -1:
        return None

    depth = 0
    in_string = False
    escape = False

    for i in range(start, len(text)):
        ch = text[i]

        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            continue

        if ch == '"':
            in_string = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]

    return None


def parse_task_plan(task_plan_raw: list[Any]) -> Optional[list[PlanningStep]]:
    """
    解析 task_plan。

    兼容：
    - 新字段名：agent_name
    - 旧字段名：agent

    规则：
    - step_id 必须是 int
    - agent 必须在允许列表中
    - action 必须是非空字符串
    - description 允许为空字符串，但必须是字符串类型
    """
    steps: list[PlanningStep] = []

    for item in task_plan_raw:
        if not isinstance(item, dict):
            return None

        step_id = item.get("step_id")
        agent = item.get("agent_name") or item.get("agent")
        action = item.get("action")
        description = item.get("description", "")

        if not isinstance(step_id, int):
            return None
        if agent not in ALLOWED_AGENTS:
            return None
        if not isinstance(action, str) or not action.strip():
            return None
        if not isinstance(description, str):
            return None

        steps.append(
            PlanningStep(
                step_id=step_id,
                agent=agent,
                action=action.strip(),
                description=description.strip(),
            )
        )

    return steps


def parse_time_range(value: Any) -> Optional[TimeRange]:
    """
    解析并校验time_range是否合法。

    要求输入必须是TimeRange：
    {
        "start_year": int,
        "start_month": int,
        "end_year": int,
        "end_month": int
    }

    不接受字符串形式的 time_range。
    若字段不完整或不合法，返回 None。
    """
    if value is None:
        return None

    if not isinstance(value, dict):
        return None

    try:
        start_year = int(value["start_year"])
        start_month = int(value["start_month"])
        end_year = int(value["end_year"])
        end_month = int(value["end_month"])
    except (KeyError, TypeError, ValueError):
        return None

    if not (1 <= start_month <= 12):
        return None
    if not (1 <= end_month <= 12):
        return None

    if (end_year, end_month) < (start_year, start_month):
        return None

    return TimeRange(
        start_year=start_year,
        start_month=start_month,
        end_year=end_year,
        end_month=end_month,
    )


def clean_optional_str(value: Any) -> Optional[str]:
    """
    将任意值清洗为 Optional[str]。
    - None -> None
    - 空白字符串 -> None
    - 其他 -> strip 后返回
    """
    if value is None:
        return None

    text = str(value).strip()
    return text if text else None


def normalize_ts_code(value: Any) -> Optional[str]:
    """
    规范化股票代码，只接受形如：
    - 000001.SZ
    - 600519.SH
    - 430047.BJ

    不合法则返回 None。
    """
    if value is None:
        return None

    text = str(value).strip().upper()
    if re.fullmatch(r"\d{6}\.(SZ|SH|BJ)", text):
        return text

    return None