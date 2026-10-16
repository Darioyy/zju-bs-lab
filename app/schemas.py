"""请求体的格式。字段类型、长度、取值范围在这里检查，不合格 FastAPI 直接返回 422。"""

from datetime import date
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class Strict(BaseModel):
    # 去掉首尾空格后再检查长度；多传了不认识的字段也报错
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")


class LoginIn(BaseModel):
    # 密码里的空格也算密码的一部分，所以不继承 Strict
    username: str = Field(min_length=1, max_length=32)
    password: str = Field(min_length=1, max_length=128)


class LeaveIn(Strict):
    kind: Literal["annual", "sick", "personal"]
    start_date: date
    end_date: date
    days: Decimal = Field(gt=0, max_digits=4, decimal_places=1)
    reason: str = Field(min_length=1, max_length=500)


class ExpenseIn(Strict):
    category: Literal["travel", "office", "meal", "other"]
    amount: Decimal = Field(gt=0, le=100000, max_digits=12, decimal_places=2)
    reason: str = Field(min_length=1, max_length=500)


class RequestBody(Strict):
    """新建和修改共用的部分。leave 和 expense 按单据类型填一个。"""

    title: str = Field(min_length=1, max_length=100)
    leave: LeaveIn | None = None
    expense: ExpenseIn | None = None


class RequestCreate(RequestBody):
    type: Literal["leave", "expense"]
    client_key: UUID


class RequestEdit(RequestBody):
    version: int


class VersionIn(Strict):
    version: int


class DecisionIn(Strict):
    version: int
    comment: str = Field(default="", max_length=500)
