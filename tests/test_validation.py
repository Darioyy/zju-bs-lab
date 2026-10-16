from datetime import date
from decimal import Decimal

from app.validation import leave_errors

D = date.fromisoformat


def test_valid_leave():
    assert leave_errors(D("2026-10-12"), D("2026-10-13"), Decimal("2")) == {}
    assert leave_errors(D("2026-10-20"), D("2026-10-22"), Decimal("2.5")) == {}
    assert leave_errors(D("2026-10-12"), D("2026-10-12"), Decimal("0.5")) == {}


def test_end_before_start():
    assert "end_date" in leave_errors(D("2026-10-13"), D("2026-10-12"), Decimal("1"))


def test_days_exceed_span():
    # 12 日到 13 日跨 2 天
    errors = leave_errors(D("2026-10-12"), D("2026-10-13"), Decimal("3"))
    assert errors == {"days": "不能超过日期跨度 2 天"}


def test_days_must_be_half_day():
    assert leave_errors(D("2026-10-12"), D("2026-10-13"), Decimal("1.3")) == {"days": "以 0.5 天为单位"}
