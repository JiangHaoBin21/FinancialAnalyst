from collections import defaultdict
from typing import Any

from app.skills.data.data_prompt_builder import build_data_user_prompt, build_data_system_prompt


class BackfillPlanSkill:
    """数据回填计划技能。"""

    def __init__(self, llm_client: Any):
        self.llm_client = llm_client

    def _call_llm(self, user_prompt: str, system_prompt: str = None) -> str:
        """
        调用大模型。
        约定 llm_client 提供 generate(user_prompt: str, system_prompt: str) -> str 接口。
        """
        return self.llm_client.generate(user_prompt=user_prompt, system_prompt=system_prompt)

    def backfill_plan(self, analysis_focus,data_completeness_check_result: dict[str, Any]):
        """
        只负责：
        完整性检查结果 -> prompt -> LLM raw response
        """
        need_backfill = defaultdict(list)
        for part in data_completeness_check_result["part_details"]:
            if not part["is_complete"]:
                need_backfill[part["part_name"]].append(part["missing_periods"])
        if not need_backfill:
            return need_backfill
        user_prompt = build_data_user_prompt()
        system_prompt = build_data_system_prompt()
        raw_response = self._call_llm(user_prompt=user_prompt, system_prompt=system_prompt)
        return raw_response