from dataclasses import asdict
from typing import Any


class CompletenessCheckSkill:
    """数据完整性检查技能。"""
    def __init__(self, completeness_checker_capability) -> None:
        self.completeness_checker_capability = completeness_checker_capability

    def skill_check(self, requested_time_range, financial_data, required_parts) -> dict[str, Any]:
        check_result = self.completeness_checker_capability.check(
            requested_time_range=requested_time_range,
            financial_data=financial_data,
            required_parts=required_parts
        )
        check_result_dict = asdict(check_result)
        return check_result_dict