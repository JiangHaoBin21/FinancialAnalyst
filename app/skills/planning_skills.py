"""负责“怎么向大模型提问，并拿回结构化规划结果”"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class PlanningStep:
    step_id: int
    agent: str
    action: str
    description: str


@dataclass
class PlanningResult:
    task_type: str
    company_name: Optional[str] = None
    ts_code: Optional[str] = None
    time_range: Optional[str] = None
    planner_message: str = ""
    next_step: str = "data"
    task_plan: list[PlanningStep] = field(default_factory=list)
    needs_user_input: bool = False
    missing_fields: list[str] = field(default_factory=list)
    raw_response: str = ""


class PlanningSkill:
    """
    任务规划 Skill

    职责：
    1. 调用大模型理解用户意图
    2. 生成结构化任务规划结果
    3. 校验大模型输出是否合法
    4. 必要时进行 fallback

    不负责：
    - 不直接修改 WorkflowState
    - 不直接执行财务数据获取
    - 不直接分析财务数据
    """

    ALLOWED_TASK_TYPES = {
        "analyze_financial_report",
        "generate_report",
        "unknown",
    }

    ALLOWED_NEXT_STEPS = {
        "supervisor",
        "data",
        "analysis",
        "report",
        "reflection",
        "finished",
        "error",
    }

    ALLOWED_AGENTS = {
        "DataAgent",
        "AnalysisAgent",
        "ReportAgent",
        "ReflectionAgent",
    }

    def __init__(self, llm_client: Any):
        self.llm_client = llm_client

    def plan_financial_task(self, user_query: str) -> PlanningResult:
        """
        对用户输入进行任务理解与规划。
        """
        prompt = self._build_planning_prompt(user_query)
        raw_response = self._call_llm(prompt)

        parsed = self._parse_json_response(raw_response)
        if parsed is None:
            return self._fallback_result(
                user_query=user_query,
                raw_response=raw_response,
                reason="llm_output_not_json",
            )

        validated = self._validate_and_build_result(parsed, raw_response)
        if validated is None:
            return self._fallback_result(
                user_query=user_query,
                raw_response=raw_response,
                reason="llm_output_invalid",
            )

        return validated

    def _build_planning_prompt(self, user_query: str) -> str:
        """
        构造给大模型的规划提示词。
        第一版先直接返回字符串，后面可以拆成 prompt template。
        """
        return f"""
你是一个多 Agent 财报分析系统中的规划器（Planning Skill）。

你的职责：
1. 识别用户任务类型
2. 提取公司名称、ts_code、时间范围
3. 生成执行计划 task_plan
4. 决定下一步 next_step

你不能直接分析财务数据，也不能直接生成最终报告。

你必须只输出 JSON，不要输出任何额外解释。

JSON Schema 要求如下：
{{
  "task_type": "analyze_financial_report | generate_report | unknown",
  "company_name": "可为空",
  "ts_code": "可为空，如 000001.SZ",
  "time_range": "可为空，如 近三年",
  "planner_message": "对规划的简短说明",
  "next_step": "supervisor | data | analysis | report | reflection | finished | error",
  "task_plan": [
    {{
      "step_id": 1,
      "agent": "DataAgent | AnalysisAgent | ReportAgent | ReflectionAgent",
      "action": "动作名",
      "description": "步骤描述"
    }}
  ],
  "needs_user_input": false,
  "missing_fields": []
}}

规则：
- 如果用户是在请求分析公司财务/财报/年报/季报，task_type 设为 "analyze_financial_report"
- 如果用户重点是让系统输出报告/总结/摘要，可设为 "generate_report"
- 如果无法识别任务，设为 "unknown"
- 如果缺少公司名称和 ts_code，needs_user_input 设为 true，missing_fields 至少包含 "company_name_or_ts_code"
- 如果 needs_user_input = true，则 next_step 应为 "finished"
- 如果信息足够，则优先从 "data" 开始
- task_plan 必须和任务匹配，且字段完整

用户输入：
{user_query}
""".strip()

    def _call_llm(self, prompt: str) -> str:
        """
        调用大模型。
        假设 llm_client 暴露 generate(prompt: str) -> str 接口。
        """
        return self.llm_client.generate(prompt)

    def _parse_json_response(self, text: str) -> Optional[dict[str, Any]]:
        """
        尝试从模型输出中提取 JSON。
        兼容 ```json ... ``` 代码块。
        """
        if not text or not text.strip():
            return None

        text = text.strip()

        # 处理 ```json ... ```
        fenced_match = re.search(r"```json\s*(\{.*\})\s*```", text, flags=re.DOTALL)
        if fenced_match:
            text = fenced_match.group(1).strip()

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # 再尝试提取第一个 {...}
        brace_match = re.search(r"(\{.*\})", text, flags=re.DOTALL)
        if brace_match:
            candidate = brace_match.group(1).strip()
            try:
                return json.loads(candidate)
            except json.JSONDecodeError:
                return None

        return None

    def _validate_and_build_result(
        self,
        data: dict[str, Any],
        raw_response: str,
    ) -> Optional[PlanningResult]:
        """
        校验 LLM 输出是否合法，并转成 PlanningResult。
        """
        task_type = data.get("task_type")
        if task_type not in self.ALLOWED_TASK_TYPES:
            return None

        next_step = data.get("next_step")
        if next_step not in self.ALLOWED_NEXT_STEPS:
            return None

        needs_user_input = bool(data.get("needs_user_input", False))
        missing_fields = data.get("missing_fields", [])
        if not isinstance(missing_fields, list):
            return None

        task_plan_raw = data.get("task_plan", [])
        if not isinstance(task_plan_raw, list):
            return None

        task_plan: list[PlanningStep] = []
        for item in task_plan_raw:
            if not isinstance(item, dict):
                return None

            step_id = item.get("step_id")
            agent = item.get("agent")
            action = item.get("action")
            description = item.get("description")

            if not isinstance(step_id, int):
                return None
            if agent not in self.ALLOWED_AGENTS:
                return None
            if not isinstance(action, str) or not action.strip():
                return None
            if not isinstance(description, str) or not description.strip():
                return None

            task_plan.append(
                PlanningStep(
                    step_id=step_id,
                    agent=agent,
                    action=action.strip(),
                    description=description.strip(),
                )
            )

        result = PlanningResult(
            task_type=task_type,
            company_name=self._clean_optional_str(data.get("company_name")),
            ts_code=self._normalize_ts_code(data.get("ts_code")),
            time_range=self._clean_optional_str(data.get("time_range")),
            planner_message=self._clean_optional_str(data.get("planner_message")) or "",
            next_step=next_step,
            task_plan=task_plan,
            needs_user_input=needs_user_input,
            missing_fields=[str(x) for x in missing_fields],
            raw_response=raw_response,
        )

        if result.needs_user_input and result.next_step != "finished":
            return None

        if result.task_type == "unknown" and not result.needs_user_input:
            # unknown 任务一般应该要求补充说明
            result.needs_user_input = True
            result.next_step = "finished"
            if "task_description" not in result.missing_fields:
                result.missing_fields.append("task_description")

        if result.task_type == "analyze_financial_report":
            if not result.company_name and not result.ts_code:
                result.needs_user_input = True
                result.next_step = "finished"
                if "company_name_or_ts_code" not in result.missing_fields:
                    result.missing_fields.append("company_name_or_ts_code")

        return result

    def _fallback_result(
        self,
        user_query: str,
        raw_response: str,
        reason: str,
    ) -> PlanningResult:
        """
        大模型输出不可用时的兜底结果。
        第一版做保守 fallback，不强行瞎规划。
        """
        return PlanningResult(
            task_type="unknown",
            company_name=None,
            ts_code=self._extract_ts_code_by_rule(user_query),
            time_range=self._extract_time_range_by_rule(user_query),
            planner_message=f"LLM 规划失败，已进入兜底流程，原因: {reason}",
            next_step="finished",
            task_plan=[],
            needs_user_input=True,
            missing_fields=["task_description", "company_name_or_ts_code"],
            raw_response=raw_response,
        )

    @staticmethod
    def _clean_optional_str(value: Any) -> Optional[str]:
        if value is None:
            return None
        text = str(value).strip()
        return text if text else None

    @staticmethod
    def _normalize_ts_code(value: Any) -> Optional[str]:
        if value is None:
            return None
        text = str(value).strip().upper()
        if re.fullmatch(r"\d{6}\.(SZ|SH|BJ)", text):
            return text
        return None

    @staticmethod
    def _extract_ts_code_by_rule(query: str) -> Optional[str]:
        match = re.search(r"\b\d{6}\.(SZ|SH|BJ)\b", query, flags=re.IGNORECASE)
        return match.group(0).upper() if match else None

    @staticmethod
    def _extract_time_range_by_rule(query: str) -> Optional[str]:
        patterns = [
            r"近\d+年",
            r"近\d+个季度",
            r"\d{4}年到\d{4}年",
            r"\d{4}-\d{4}",
            r"\d{4}年",
        ]
        for pattern in patterns:
            match = re.search(pattern, query)
            if match:
                return match.group(0)
        return None