"""通用工具函数"""

import pandas as pd

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