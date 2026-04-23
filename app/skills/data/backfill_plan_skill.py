from collections import defaultdict
from typing import Any


class BackfillPlanSkill:
    """数据回填计划技能。"""

    def __init__(self, llm_client: Any):
        self.llm_client = llm_client

    def _call_llm(self, prompt: str) -> str:
        """
        调用大模型。
        约定 llm_client 提供 generate(prompt: str) -> str 接口。
        """
        return self.llm_client.generate(prompt)

    def backfill_plan(self, analysis_focus,data_completeness_check_result: dict[str, Any]):
        """
        只负责：
        完整性检查结果 -> prompt -> LLM raw response
        """
        need_backfill = defaultdict(list)
        for part in data_completeness_check_result["part_details"]:
            if part["is_complete"]:
                need_backfill[part["part_name"]].append(part["missing_periods"])
        prompt = ""
        raw_response = self._call_llm(prompt)
        return raw_response