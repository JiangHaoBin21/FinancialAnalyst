# app/skills/planning/planning_policy.py

from __future__ import annotations

import copy
import re
from datetime import datetime
from typing import Optional

from app.domain.models import PlanningResult, PlanningStep, TimeRange


def finalize_planning_result(
    parsed_result: Optional[PlanningResult],
    user_query: str,
    raw_response: str,
) -> PlanningResult:
    """
    对 parser 输出做最终业务层处理。

    职责：
    1. 如果 parser 失败，给出 fallback result
    2. 对 parser 成功结果做规则补充
    3. 做业务必填判断
    4. 必要时补默认 task_plan
    5. 对 task_plan 做轻量语义校验
    """
    if parsed_result is None:
        return fallback_result(
            user_query=user_query,
            raw_response=raw_response,
            reason="llm_output_invalid_or_unparseable",
        )

    result = copy.deepcopy(parsed_result)

    # ---- 规则补充：从 query 再做一次兜底抽取 ----
    if result.ts_code is None:
        result.ts_code = extract_ts_code_by_rule(user_query)

    if result.time_range is None:
        result.time_range = extract_time_range_by_rule(user_query)

    if result.analysis_focus is None:
        result.analysis_focus = extract_analysis_focus_by_rule(user_query)

    if result.output_mode == "report" and looks_like_summary_request(user_query):
        result.output_mode = "summary"

    # ---- unknown 任务处理 ----
    if result.task_type == "unknown":
        result.needs_user_input = True
        if "task_description" not in result.missing_fields:
            result.missing_fields.append("task_description")

    # ---- financial_analysis 必填信息校验 ----
    if result.task_type == "financial_analysis":
        if not result.company_name and not result.ts_code:
            result.needs_user_input = True
            if "company_name_or_ts_code" not in result.missing_fields:
                result.missing_fields.append("company_name_or_ts_code")

    # ---- 若 LLM 没给 plan，则代码补一个默认高层 plan ----
    if not result.task_plan and not result.needs_user_input:
        result.task_plan = build_default_plan(
            task_type=result.task_type,
            output_mode=result.output_mode,
        )

    # ---- 对 plan 做轻量语义校验 ----
    normalized_plan = normalize_and_validate_plan(
        task_type=result.task_type,
        task_plan=result.task_plan,
        needs_user_input=result.needs_user_input,
    )

    if normalized_plan is None:
        return fallback_result(
            user_query=user_query,
            raw_response=raw_response,
            reason="task_plan_invalid",
        )

    result.task_plan = normalized_plan
    result.raw_response = raw_response

    return result


def build_default_plan(task_type: str, output_mode: str) -> list[PlanningStep]:
    """
    当 LLM 没给可用 plan，但基础信息足够时，由代码补一个保守默认计划。
    """
    if task_type != "financial_analysis":
        return []

    steps = [
        PlanningStep(
            step_id=1,
            agent="DataAgent",
            action="fetch_financial_data",
            description="获取并准备目标公司的财务数据",
        ),
        PlanningStep(
            step_id=2,
            agent="AnalysisAgent",
            action="analyze_financial_health",
            description="分析公司的财务表现、趋势与风险",
        ),
    ]

    if output_mode == "summary":
        steps.append(
            PlanningStep(
                step_id=3,
                agent="ReportAgent",
                action="generate_summary",
                description="生成简要结论与摘要",
            )
        )
    else:
        steps.append(
            PlanningStep(
                step_id=3,
                agent="ReportAgent",
                action="generate_financial_report",
                description="生成完整财务分析报告",
            )
        )

    return steps


def normalize_and_validate_plan(
    task_type: str,
    task_plan: list[PlanningStep],
    needs_user_input: bool,
) -> Optional[list[PlanningStep]]:
    """
    对 plan 做轻量语义校验和标准化。

    规则：
    1. 若需要用户补充信息，则 plan 应为空
    2. unknown 任务不应继续执行具体步骤
    3. step_id 重新标准化为 1..N
    4. financial_analysis 的首步不能是 ReportAgent / ReflectionAgent
    5. ReportAgent 不能出现在 DataAgent 之前
    6. ReflectionAgent 通常不应在第一步
    """
    if needs_user_input:
        return []

    if task_type == "unknown":
        return []

    if not task_plan:
        return []

    task_plan = sorted(task_plan, key=lambda x: x.step_id)

    normalized: list[PlanningStep] = []
    for idx, step in enumerate(task_plan, start=1):
        normalized.append(
            PlanningStep(
                step_id=idx,
                agent=step.agent,
                action=step.action,
                description=step.description,
            )
        )

    first_agent = normalized[0].agent
    if task_type == "financial_analysis":
        if first_agent in {"ReportAgent", "ReflectionAgent"}:
            return None

    seen_data = False
    for step in normalized:
        if step.agent == "DataAgent":
            seen_data = True

        if step.agent == "ReportAgent" and not seen_data:
            return None

        if step.agent == "ReflectionAgent" and step.step_id == 1:
            return None

    return normalized


def fallback_result(
    user_query: str,
    raw_response: str,
    reason: str,
) -> PlanningResult:
    """
    当 parser 失败或规划结果不可接受时的兜底结果。
    """
    ts_code = extract_ts_code_by_rule(user_query)
    time_range = extract_time_range_by_rule(user_query)
    analysis_focus = extract_analysis_focus_by_rule(user_query)
    output_mode = "summary" if looks_like_summary_request(user_query) else "report"

    if looks_like_financial_analysis_request(user_query):
        if ts_code:
            task_type = "financial_analysis"
            task_plan = build_default_plan(task_type=task_type, output_mode=output_mode)
            return PlanningResult(
                task_type=task_type,
                company_name=None,
                ts_code=ts_code,
                time_range=time_range,
                analysis_focus=analysis_focus,
                output_mode=output_mode,
                planner_message=f"LLM 规划失败，已使用规则兜底恢复执行计划，原因: {reason}",
                task_plan=task_plan,
                needs_user_input=False,
                missing_fields=[],
                raw_response=raw_response,
            )

        return PlanningResult(
            task_type="financial_analysis",
            company_name=None,
            ts_code=None,
            time_range=time_range,
            analysis_focus=analysis_focus,
            output_mode=output_mode,
            planner_message=f"LLM 规划失败，已进入补充信息流程，原因: {reason}",
            task_plan=[],
            needs_user_input=True,
            missing_fields=["company_name_or_ts_code"],
            raw_response=raw_response,
        )

    return PlanningResult(
        task_type="unknown",
        company_name=None,
        ts_code=ts_code,
        time_range=time_range,
        analysis_focus=analysis_focus,
        output_mode=output_mode,
        planner_message=f"LLM 规划失败，且规则无法可靠识别任务，原因: {reason}",
        task_plan=[],
        needs_user_input=True,
        missing_fields=["task_description"],
        raw_response=raw_response,
    )


def extract_ts_code_by_rule(query: str) -> Optional[str]:
    match = re.search(r"\b\d{6}\.(SZ|SH|BJ)\b", query, flags=re.IGNORECASE)
    return match.group(0).upper() if match else None


def extract_time_range_by_rule(query: str) -> Optional[TimeRange]:
    """
    仅做非常保守的规则提取。
    当前支持：
    - 近N年
    - YYYY年到YYYY年
    - YYYY-YYYY
    - 单一年份 YYYY年
    """
    now = datetime.now()

    match = re.search(r"近(\d+)年", query)
    if match:
        n = int(match.group(1))
        start_year = now.year - n
        return TimeRange(
            start_year=start_year,
            start_month=1,
            end_year=now.year,
            end_month=now.month,
        )

    match = re.search(r"(\d{4})年到(\d{4})年", query)
    if match:
        start_year = int(match.group(1))
        end_year = int(match.group(2))
        return TimeRange(
            start_year=start_year,
            start_month=1,
            end_year=end_year,
            end_month=12,
        )

    match = re.search(r"(\d{4})-(\d{4})", query)
    if match:
        start_year = int(match.group(1))
        end_year = int(match.group(2))
        return TimeRange(
            start_year=start_year,
            start_month=1,
            end_year=end_year,
            end_month=12,
        )

    match = re.search(r"(\d{4})年", query)
    if match:
        year = int(match.group(1))
        return TimeRange(
            start_year=year,
            start_month=1,
            end_year=year,
            end_month=12,
        )

    return None


def extract_analysis_focus_by_rule(query: str) -> Optional[str]:
    mapping = {
        "盈利能力": ["盈利能力", "利润", "毛利率", "净利率", "赚钱能力"],
        "偿债能力": ["偿债能力", "负债", "现金流压力", "债务"],
        "成长性": ["成长性", "增长", "营收增长", "扩张"],
        "综合财务表现": ["财务情况", "财务表现", "财务分析", "综合表现", "经营情况"],
        "风险分析": ["风险", "风险点", "潜在问题"],
    }

    for focus, keywords in mapping.items():
        for kw in keywords:
            if kw in query:
                return focus
    return None


def looks_like_summary_request(query: str) -> bool:
    keywords = ["简短", "简单总结", "摘要", "总结一下", "简要", "一句话", "简述"]
    return any(kw in query for kw in keywords)


def looks_like_financial_analysis_request(query: str) -> bool:
    keywords = [
        "财务",
        "财报",
        "年报",
        "季报",
        "经营情况",
        "经营表现",
        "盈利能力",
        "偿债能力",
        "成长性",
        "风险",
        "分析",
        "报告",
        "总结",
    ]
    return any(kw in query for kw in keywords)