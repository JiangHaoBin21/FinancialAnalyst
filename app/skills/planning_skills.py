"""负责“怎么向大模型提问，并拿回结构化规划结果”"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Optional


# =========================
# 1) 内部数据结构
# =========================

@dataclass
class PlanningStep:
    """单个规划步骤。"""

    step_id: int
    agent: str
    action: str
    description: str


@dataclass
class PlanningResult:
    """
    规划结果（系统内部标准对象）。

    注意：
    - 这是 Python 内部使用的真实对象
    - 不是直接给 LLM 的 schema
    """

    task_type: str
    company_name: Optional[str] = None
    ts_code: Optional[str] = None
    time_range: Optional[str] = None
    analysis_focus: Optional[str] = None
    output_mode: str = "report"  # report | summary
    planner_message: str = ""
    next_step: str = "await_user_input"
    task_plan: list[PlanningStep] = field(default_factory=list)
    needs_user_input: bool = False
    missing_fields: list[str] = field(default_factory=list)
    raw_response: str = ""


# =========================
# 2) Agent Registry / Catalog
# =========================

AGENT_REGISTRY: dict[str, dict[str, Any]] = {
    "DataAgent": {
        "responsibilities": [
            "识别当前任务需要哪些财务数据",
            "查询本地数据库是否已有目标公司数据",
            "必要时调用外部数据源（如 TuShare）拉取数据",
            "输出结构化财务数据结果",
        ],
        "cannot_do": [
            "不负责深度财务结论分析",
            "不负责生成最终面向用户的报告",
        ],
        "typical_actions": [
            "fetch_financial_data",
            "load_company_profile",
            "check_data_freshness",
            "sync_financial_statements",
        ],
    },
    "AnalysisAgent": {
        "responsibilities": [
            "基于已有财务数据做指标计算",
            "进行趋势分析、结构分析、风险识别",
            "输出结构化分析结论",
        ],
        "cannot_do": [
            "不负责原始数据拉取",
            "不负责最终报告排版输出",
        ],
        "typical_actions": [
            "analyze_financial_health",
            "analyze_profitability",
            "analyze_solvency",
            "analyze_growth",
            "identify_risks",
        ],
    },
    "ReportAgent": {
        "responsibilities": [
            "将分析结果组织成自然语言报告、摘要或结论",
            "根据用户要求输出详细报告或简要总结",
        ],
        "cannot_do": [
            "不负责原始财务数据拉取",
            "不负责底层指标计算",
        ],
        "typical_actions": [
            "generate_financial_report",
            "generate_summary",
            "draft_conclusion",
        ],
    },
    "ReflectionAgent": {
        "responsibilities": [
            "检查分析或报告是否存在遗漏、逻辑矛盾、证据不足",
            "提出修正建议，必要时要求回退重做",
        ],
        "cannot_do": [
            "不负责原始数据拉取",
        ],
        "typical_actions": [
            "review_analysis_result",
            "review_report_quality",
            "request_replan",
        ],
    },
}


# =========================
# 3) Planning Skill
# =========================

class PlanningSkill:
    """
    任务规划 Skill

    职责：
    1. 调用大模型理解用户意图
    2. 提取公司、时间范围、分析重点等关键参数
    3. 生成高层 task_plan
    4. 由代码对结果进行校验、修正与 next_step 推导
    5. 必要时使用 rule-based fallback

    不负责：
    - 不直接修改 WorkflowState
    - 不直接执行数据获取
    - 不直接执行分析
    - 不直接生成最终报告
    """

    ALLOWED_TASK_TYPES = {
        "financial_analysis",
        "unknown",
    }

    ALLOWED_OUTPUT_MODES = {
        "report",
        "summary",
    }

    ALLOWED_NEXT_STEPS = {
        "supervisor",
        "data",
        "analysis",
        "report",
        "reflection",
        "await_user_input",
        "finished",
        "error",
    }

    ALLOWED_AGENTS = set(AGENT_REGISTRY.keys())

    def __init__(self, llm_client: Any):
        self.llm_client = llm_client

    # =========================
    # 3.1 对外主入口
    # =========================

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

        validated = self._validate_and_build_result(
            data=parsed,
            raw_response=raw_response,
            user_query=user_query,
        )
        if validated is None:
            return self._fallback_result(
                user_query=user_query,
                raw_response=raw_response,
                reason="llm_output_invalid",
            )

        return validated

    # =========================
    # 3.2 Prompt 构造
    # =========================

    def _build_planning_prompt(self, user_query: str) -> str:
        """
        构造给大模型的规划提示词。
        """

        agent_catalog_text = self._render_agent_catalog()

        return f"""
你是一个多 Agent 财报分析系统中的规划器（Planning Skill）。

你的职责：
1. 理解用户任务意图
2. 提取关键任务参数
3. 生成高层执行计划 task_plan
4. 只输出结构化 JSON，不输出任何额外解释

请注意：
- 你负责“任务理解和高层规划”
- 你不负责直接执行数据获取、分析、报告生成
- 你输出的是“规划建议”，系统代码会进一步校验和决定实际 next_step

====================
【系统中的可用 Agent 及能力边界】
====================
{agent_catalog_text}

====================
【规划规则】
====================
1. 如果用户想分析某家上市公司的财务情况、财报、年报、季报、经营表现、风险情况：
   - task_type 设为 "financial_analysis"

2. 如果无法识别用户任务，设为 "unknown"

3. 如果用户明确要求“简单总结/简短结论/摘要”，output_mode 设为 "summary"
   否则默认设为 "report"

4. 如果缺少执行任务所必需的信息：
   - needs_user_input 设为 true
   - missing_fields 填写缺失字段名列表
   - task_plan 可以为空，或者只给出非常高层的说明

5. 对于财务分析类任务，常见顺序通常是：
   - 先 DataAgent
   - 再 AnalysisAgent
   - 再 ReportAgent
   - 如有必要最后 ReflectionAgent
   但如果任务只要求查看已有数据，可缩短计划

6. 不要让 ReportAgent 在没有数据和分析结论的情况下直接产出最终报告
7. 不要让 AnalysisAgent 在没有数据准备的情况下先进行深度分析
8. ReflectionAgent 通常用于质量检查，而不是主执行入口

====================
【输出 JSON Schema】
====================
{{
  "task_type": "financial_analysis | unknown",
  "company_name": "可为空",
  "ts_code": "可为空，如 000001.SZ",
  "time_range": "可为空，如 近三年 / 2022年到2024年",
  "analysis_focus": "可为空，如 盈利能力/偿债能力/成长性/综合财务表现",
  "output_mode": "report | summary",
  "planner_message": "对规划结果的简短说明",
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

====================
【缺失字段命名规范】
====================
只允许优先使用这些字段名：
- company_name
- ts_code
- company_name_or_ts_code
- time_range
- analysis_focus
- task_description

====================
【用户输入】
====================
{user_query}
""".strip()

    def _render_agent_catalog(self) -> str:
        """
        将 AGENT_REGISTRY 渲染为 prompt 文本。
        """
        lines: list[str] = []

        for agent_name, meta in AGENT_REGISTRY.items():
            lines.append(f"{agent_name}:")
            responsibilities = meta.get("responsibilities", [])
            cannot_do = meta.get("cannot_do", [])
            typical_actions = meta.get("typical_actions", [])

            if responsibilities:
                lines.append("  - 职责：")
                for item in responsibilities:
                    lines.append(f"    - {item}")

            if cannot_do:
                lines.append("  - 不负责：")
                for item in cannot_do:
                    lines.append(f"    - {item}")

            if typical_actions:
                lines.append("  - 典型动作：")
                for item in typical_actions:
                    lines.append(f"    - {item}")

            lines.append("")

        return "\n".join(lines).strip()

    # =========================
    # 3.3 LLM 调用
    # =========================

    def _call_llm(self, prompt: str) -> str:
        """
        调用大模型。
        假设 llm_client 暴露 generate(prompt: str) -> str 接口。
        """
        return self.llm_client.generate(prompt)

    # =========================
    # 3.4 解析 JSON
    # =========================

    def _parse_json_response(self, text: str) -> Optional[dict[str, Any]]:
        """
        尝试从模型输出中提取 JSON。
        优先直接 json.loads，其次兼容 ```json ... ``` 代码块，
        最后再尝试提取第一个平衡的 JSON 对象。
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
        fenced_match = re.search(r"```json\s*(.*?)\s*```", text, flags=re.DOTALL | re.IGNORECASE)
        if fenced_match:
            fenced_text = fenced_match.group(1).strip()
            try:
                parsed = json.loads(fenced_text)
                return parsed if isinstance(parsed, dict) else None
            except json.JSONDecodeError:
                pass

        # 3) 提取第一个平衡的 {...}
        candidate = self._extract_first_balanced_json_object(text)
        if candidate:
            try:
                parsed = json.loads(candidate)
                return parsed if isinstance(parsed, dict) else None
            except json.JSONDecodeError:
                return None

        return None

    @staticmethod
    def _extract_first_balanced_json_object(text: str) -> Optional[str]:
        """
        从文本中提取第一个括号平衡的 JSON 对象。
        相比简单正则 r"(\\{{.*\\}})" 更稳一些。
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
                    return text[start:i + 1]

        return None

    # =========================
    # 3.5 校验、修正、构建结果
    # =========================

    def _validate_and_build_result(
        self,
        data: dict[str, Any],
        raw_response: str,
        user_query: str,
    ) -> Optional[PlanningResult]:
        """
        校验 LLM 输出是否合法，并转成 PlanningResult。
        同时由代码修正部分字段，并推导 next_step。
        """

        # ---- task_type ----
        task_type = self._clean_optional_str(data.get("task_type")) or "unknown"
        if task_type not in self.ALLOWED_TASK_TYPES:
            return None

        # ---- 基本字段 ----
        company_name = self._clean_optional_str(data.get("company_name"))
        ts_code = self._normalize_ts_code(data.get("ts_code"))
        time_range = self._clean_optional_str(data.get("time_range"))
        analysis_focus = self._clean_optional_str(data.get("analysis_focus"))

        output_mode = self._clean_optional_str(data.get("output_mode")) or "report"
        if output_mode not in self.ALLOWED_OUTPUT_MODES:
            output_mode = "report"

        planner_message = self._clean_optional_str(data.get("planner_message")) or ""

        needs_user_input = bool(data.get("needs_user_input", False))

        missing_fields_raw = data.get("missing_fields", [])
        if not isinstance(missing_fields_raw, list):
            return None
        missing_fields = [str(x).strip() for x in missing_fields_raw if str(x).strip()]

        # ---- task_plan ----
        task_plan_raw = data.get("task_plan", [])
        if not isinstance(task_plan_raw, list):
            return None

        task_plan = self._parse_task_plan(task_plan_raw)
        if task_plan is None:
            return None

        # ---- 规则补充：从 query 再做一次兜底抽取 ----
        if ts_code is None:
            ts_code = self._extract_ts_code_by_rule(user_query)

        if time_range is None:
            time_range = self._extract_time_range_by_rule(user_query)

        if analysis_focus is None:
            analysis_focus = self._extract_analysis_focus_by_rule(user_query)

        if output_mode == "report" and self._looks_like_summary_request(user_query):
            output_mode = "summary"

        # ---- unknown 任务处理 ----
        if task_type == "unknown":
            needs_user_input = True
            if "task_description" not in missing_fields:
                missing_fields.append("task_description")

        # ---- financial_analysis 必填信息校验 ----
        if task_type == "financial_analysis":
            if not company_name and not ts_code:
                needs_user_input = True
                if "company_name_or_ts_code" not in missing_fields:
                    missing_fields.append("company_name_or_ts_code")

        # ---- 若 LLM 没给 plan，则代码尝试生成一个默认高层 plan ----
        if not task_plan and not needs_user_input:
            task_plan = self._build_default_plan(
                task_type=task_type,
                output_mode=output_mode,
            )

        # ---- 语义校验：task_plan 顺序是否合理 ----
        task_plan = self._normalize_and_validate_plan(
            task_type=task_type,
            task_plan=task_plan,
            needs_user_input=needs_user_input,
            output_mode=output_mode,
        )
        if task_plan is None:
            return None

        # ---- 由代码推导 next_step ----
        next_step = self._derive_next_step(
            task_type=task_type,
            needs_user_input=needs_user_input,
            task_plan=task_plan,
        )

        result = PlanningResult(
            task_type=task_type,
            company_name=company_name,
            ts_code=ts_code,
            time_range=time_range,
            analysis_focus=analysis_focus,
            output_mode=output_mode,
            planner_message=planner_message,
            next_step=next_step,
            task_plan=task_plan,
            needs_user_input=needs_user_input,
            missing_fields=missing_fields,
            raw_response=raw_response,
        )

        return result

    def _parse_task_plan(self, task_plan_raw: list[Any]) -> Optional[list[PlanningStep]]:
        """
        解析 task_plan 列表。
        """
        steps: list[PlanningStep] = []

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

            steps.append(
                PlanningStep(
                    step_id=step_id,
                    agent=agent,
                    action=action.strip(),
                    description=description.strip(),
                )
            )

        return steps

    def _build_default_plan(self, task_type: str, output_mode: str) -> list[PlanningStep]:
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

    def _normalize_and_validate_plan(
        self,
        task_type: str,
        task_plan: list[PlanningStep],
        needs_user_input: bool,
        output_mode: str,
    ) -> Optional[list[PlanningStep]]:
        """
        对 LLM 给出的 plan 做轻量语义校验和标准化。

        当前规则：
        1. 若需要用户补充信息，则 plan 应为空或忽略
        2. step_id 重新标准化为 1..N
        3. financial_analysis 的首步不能是 ReportAgent / ReflectionAgent
        4. ReportAgent 不能出现在 DataAgent 之前
        5. ReflectionAgent 通常不应在第一步
        """
        if needs_user_input:
            return []

        if task_type == "unknown":
            return []

        if not task_plan:
            return []

        # 重新排序并标准化 step_id
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

    def _derive_next_step(
        self,
        task_type: str,
        needs_user_input: bool,
        task_plan: list[PlanningStep],
    ) -> str:
        """
        由代码推导实际 next_step，而不是直接相信 LLM。
        """
        if needs_user_input:
            return "await_user_input"

        if task_type == "unknown":
            return "await_user_input"

        if not task_plan:
            return "error"

        first_agent = task_plan[0].agent

        agent_to_step = {
            "DataAgent": "data",
            "AnalysisAgent": "analysis",
            "ReportAgent": "report",
            "ReflectionAgent": "reflection",
        }

        return agent_to_step.get(first_agent, "error")

    # =========================
    # 3.6 Fallback
    # =========================

    def _fallback_result(
        self,
        user_query: str,
        raw_response: str,
        reason: str,
    ) -> PlanningResult:
        """
        大模型输出不可用时的兜底结果。

        改进点：
        - 不再一律退回 unknown
        - 尝试基于规则恢复成一个可执行 planning result
        """
        ts_code = self._extract_ts_code_by_rule(user_query)
        time_range = self._extract_time_range_by_rule(user_query)
        analysis_focus = self._extract_analysis_focus_by_rule(user_query)
        output_mode = "summary" if self._looks_like_summary_request(user_query) else "report"

        # 基于关键词判断是否像财务分析请求
        if self._looks_like_financial_analysis_request(user_query):
            if ts_code:
                task_type = "financial_analysis"
                task_plan = self._build_default_plan(task_type=task_type, output_mode=output_mode)
                return PlanningResult(
                    task_type=task_type,
                    company_name=None,
                    ts_code=ts_code,
                    time_range=time_range,
                    analysis_focus=analysis_focus,
                    output_mode=output_mode,
                    planner_message=f"LLM 规划失败，已使用规则兜底恢复执行计划，原因: {reason}",
                    next_step="data",
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
                next_step="await_user_input",
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
            next_step="await_user_input",
            task_plan=[],
            needs_user_input=True,
            missing_fields=["task_description"],
            raw_response=raw_response,
        )

    # =========================
    # 3.7 工具函数
    # =========================

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
            r"近\d+个月",
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

    @staticmethod
    def _extract_analysis_focus_by_rule(query: str) -> Optional[str]:
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

    @staticmethod
    def _looks_like_summary_request(query: str) -> bool:
        keywords = ["简短", "简单总结", "摘要", "总结一下", "简要", "一句话", "简述"]
        return any(kw in query for kw in keywords)

    @staticmethod
    def _looks_like_financial_analysis_request(query: str) -> bool:
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