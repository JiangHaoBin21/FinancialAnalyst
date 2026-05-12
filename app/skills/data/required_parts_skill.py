from typing import Any

from app.skills.data.data_prompt_builder import build_data_plan_user_prompt, build_data_plan_system_prompt
from app.skills.planning.planning_parser import parse_json_response


class RequiredPartsSkill:
    """规划数据需求skill。"""
    def __init__(self, llm_client):
        self.llm_client = llm_client

    def _call_llm(self, user_prompt: str, system_prompt: str = None) -> str:
        """
        调用大模型。
        约定 llm_client 提供 generate(user_prompt: str, system_prompt: str) -> str 接口。
        """
        return self.llm_client.generate(user_prompt=user_prompt, system_prompt=system_prompt)

    def plan_required_parts(self, user_query: str, analysis_focus: str) -> dict[str, Any] | None:
        user_prompt = build_data_plan_user_prompt(user_query, analysis_focus)
        system_prompt = build_data_plan_system_prompt()
        raw_response = self._call_llm(user_prompt=user_prompt, system_prompt=system_prompt)
        return parse_json_response(raw_response)