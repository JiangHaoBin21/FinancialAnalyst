from __future__ import annotations

from datetime import date
from typing import Any, Optional
import pandas as pd


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

def generate_quarter_ends(start_str: str, end_str: str):
    """根据开始和结束年月自动生成每季度最后一天的日期"""
    # 将输入格式转换为 pandas 识别的日期格式
    start_dt = pd.to_datetime(start_str.replace('.', '-'))
    end_dt = pd.to_datetime(end_str.replace('.', '-')) + pd.offsets.MonthEnd(0)

    # 'QE' 表示 Quarter End (季度末)
    # 这里的 freq='QE' 会自动寻找窗口内的 3/31, 6/30, 9/30, 12/31
    dates = pd.date_range(start=start_dt, end=end_dt, freq='QE')

    return [d.strftime('%Y-%m-%d') for d in dates]


def get_last_day_of_month(year_month_str: str):
    # 1. 将字符串解析为日期（默认会指向该月1号）
    # 例如 "2024.2" -> 2024-02-01
    dt = pd.to_datetime(year_month_str.replace('.', '-'))

    # 2. 使用 MonthEnd(0) 自动滚动到当前月份的最后一天
    last_day = dt + pd.offsets.MonthEnd(0)

    return last_day.strftime('%Y%m%d')


def get_first_day_of_month(year_month_str: str):
    # 1. 解析日期
    dt = pd.to_datetime(year_month_str.replace('.', '-'))

    # 2. 强制滚动到当月 1 号
    first_day = dt.replace(day=1)

    return first_day.strftime('%Y%m%d')

# 测试
res = generate_quarter_ends("2022.1", "2024.6")
res1 = get_last_day_of_month("2024.6")
res2 = get_first_day_of_month("2024.6")
print(res1, res2)