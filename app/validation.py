"""跨字段的校验规则。单个字段的格式、长度、范围在 schemas.py 里由 pydantic 检查。"""

from datetime import date
from decimal import Decimal


def leave_errors(start: date, end: date, days: Decimal) -> dict[str, str]:
    errors = {}
    if days * 2 % 1 != 0:
        errors["days"] = "以 0.5 天为单位"
    if end < start:
        errors["end_date"] = "结束日期不能早于开始日期"
    else:
        span = (end - start).days + 1
        if days > span:
            errors["days"] = f"不能超过日期跨度 {span} 天"
    return errors
