# app/skills/planning/planning_skill.py

"""负责调用 planner 大模型，并串联 prompt builder、parser、policy。"""

from __future__ import annotations

from typing import Any

from app.domain.planning_models import PlanningResult
from app.skills.planning.planning_parser import parse_planning_result
from app.skills.planning.planning_policy import finalize_planning_result
from app.skills.planning.planning_prompt_builder import build_planning_prompt


class PlanningSkill:
    """
    Planning Skill

    职责：
    1. 根据用户输入构造 planner prompt
    2. 调用大模型获取原始规划结果
    3. 调用 parser 将原始输出解析为结构化结果
    4. 调用 policy 对解析结果做最终收口

    不负责：
    - 不直接修改 WorkflowState
    - 不直接执行 Data/Analysis/Report 等下游任务
    - 不在这里实现 fallback 细节、默认 plan 细节、规则兜底细节
    """

    def __init__(self, llm_client: Any):
        self.llm_client = llm_client

    def _call_llm(self, prompt: str) -> str:
        """
        调用大模型。
        约定 llm_client 提供 generate(prompt: str) -> str 接口。
        """
        return self.llm_client.generate(prompt)

    def generate_raw_plan(self, user_query: str) -> str:
        """
        只负责：
        用户输入 -> prompt -> LLM raw response
        """
        prompt = build_planning_prompt(user_query)
        raw_response = self._call_llm(prompt)
        return raw_response

    def plan_financial_task(self, user_query: str) -> PlanningResult:
        """
        对外主入口：
        user_query
          -> prompt_builder
          -> llm
          -> parser
          -> policy
          -> final PlanningResult
        """
        raw_response = self.generate_raw_plan(user_query)

        parsed_result = parse_planning_result(raw_response)

        final_result = finalize_planning_result(
            parsed_result=parsed_result,
            user_query=user_query,
            raw_response=raw_response,
        )

        return final_result