"""数据库相关处理函数"""
from __future__ import annotations

from datetime import date
from typing import Any, Optional
from app.core.config import settings
from requests import Session
from app.repositories.income_repo import IncomeRepository


def should_replace_by_update_flag(
    existing_update_flag: Optional[str],
    incoming_update_flag: Optional[str],
) -> bool:
    """
    update_flag 版本优先级规则：

    - 若旧记录是修正版(update_flag='1')，新记录不是 '1'，则不覆盖
    - 其他情况允许覆盖

    适用前提：
    调用方已经先按“业务唯一键”查到了 existing record。
    """
    old_flag = (existing_update_flag or "").strip()
    new_flag = (incoming_update_flag or "").strip()

    if old_flag == "1" and new_flag != "1":
        return False

    return True

# def get_record_by_part_and_time_range(
#     db: Session,
#     ts_code: str,
#     part_name: str,
#     start_date_obj: date,
#     end_date_obj: date,
#     repo
# ):
#     """
#     按表明和指定时间范围查询记录
#     """
#     if part_name not in settings.CORE_FINANCIAL_PARTS:
#         raise ValueError(f"非法的财务数据表名: {part_name}")
#     if part_name == "income":

def get_repo_from_part_name(
        part_name: str,
        list_of_repos: list[Any],
) -> Any:
    """
    根据表名获取对应的 Repo
    """
    if part_name == settings.CORE_FINANCIAL_PARTS[0]:
        return list_of_repos[0]
    elif part_name == settings.CORE_FINANCIAL_PARTS[1]:
        return list_of_repos[1]
    elif part_name == settings.CORE_FINANCIAL_PARTS[2]:
        return list_of_repos[2]
    else:
        return list_of_repos[3]
