"""数据库相关处理函数"""
from __future__ import annotations

from datetime import date
from typing import Any, Optional
from app.core.config import settings
from requests import Session

from sqlalchemy import inspect

def model_to_dict(model_obj):
    """
    将 SQLAlchemy 模型对象转换为字典
    """
    return {c.key: getattr(model_obj, c.key) for c in inspect(model_obj).mapper.column_attrs}


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

def get_repo_or_func_from_part_name(
        part_name: str,
        list_of_repos: list[Any] = None,
        tushare: Any = None,
) -> Any:
    """
    根据表名获取对应的 Repo
    """
    if list_of_repos:
        part_name_to_repo = {
            settings.CORE_FINANCIAL_PARTS[0]: list_of_repos[0],
            settings.CORE_FINANCIAL_PARTS[1]: list_of_repos[1],
            settings.CORE_FINANCIAL_PARTS[2]: list_of_repos[2],
            settings.CORE_FINANCIAL_PARTS[3]: list_of_repos[3],
        }
        return part_name_to_repo.get(part_name)
    else:
        part_name_to_tushare = {
            settings.CORE_FINANCIAL_PARTS[0]: tushare.get_income_records,
            settings.CORE_FINANCIAL_PARTS[1]: tushare.get_balance_sheet_records,
            settings.CORE_FINANCIAL_PARTS[2]: tushare.get_cashflow_records,
            settings.CORE_FINANCIAL_PARTS[3]: tushare.get_fina_indicator_records,
        }
        return part_name_to_tushare.get(part_name)

def get_records_from_date_and_required_parts(
        db: Session,
        ts_code,
        start_date_obj: date,
        end_date_obj: date,
        required_parts: list,
        list_of_repos: list
) -> list[dict]:
    """封装的根据日期和表明获取记录"""
    raw_financial_data = []
    for part_name in required_parts:
        if part_name not in settings.CORE_FINANCIAL_PARTS:
            raise ValueError(f"非法的财务数据表名: {part_name}")
        repo = get_repo_or_func_from_part_name(part_name, list_of_repos)
        for item in repo.list_by_ts_code_and_date_range(
            db=db,
            ts_code=ts_code,
            start_date=start_date_obj,
            end_date=end_date_obj
        ):
            raw_financial_data.append(model_to_dict(item))
    return raw_financial_data
