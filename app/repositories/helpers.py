from __future__ import annotations

from datetime import date
from typing import Any, Optional


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