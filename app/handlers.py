"""把异常统一转成 JSON 响应。

返回体都是 {"detail": ...}：
- 一般错误，detail 是一句话；
- 输入错误（422），detail 是列表，每项 {"loc": ["body", 字段...], "msg": 原因}。
  FastAPI 自带的参数校验错误也是这个格式，前端只用处理一种。
"""

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from psycopg import errors as pg_errors

from .errors import AppError, Invalid

# pydantic 的错误类型 → 中文提示，{} 里的值从错误的 ctx 里取
MESSAGES = {
    "missing": "必填",
    "string_too_short": "不能为空",
    "string_too_long": "不能超过 {max_length} 个字",
    "string_type": "必须是文字",
    "string_pattern_mismatch": "格式不对",
    "int_parsing": "必须是整数",
    "int_type": "必须是整数",
    "greater_than": "必须大于 {gt}",
    "less_than_equal": "不能超过 {le}",
    "decimal_parsing": "必须是数字",
    "decimal_max_places": "最多 {decimal_places} 位小数",
    "decimal_max_digits": "数字太大",
    "decimal_whole_digits": "整数部分太长",
    "date_parsing": "日期格式不对",
    "date_from_datetime_parsing": "日期格式不对",
    "literal_error": "不在可选范围内",
    "uuid_parsing": "格式不对",
    "extra_forbidden": "不认识的字段",
    "json_invalid": "不是合法的 JSON",
}


def translate(error: dict) -> str:
    if error["type"] == "string_too_short" and error.get("ctx", {}).get("min_length", 1) > 1:
        return f"至少 {error['ctx']['min_length']} 个字符"
    template = MESSAGES.get(error["type"])
    if template is None:
        return error["msg"]
    try:
        return template.format(**error.get("ctx", {}))
    except (KeyError, IndexError):
        return template


def install(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def app_error(request: Request, exc: AppError):
        if isinstance(exc, Invalid):
            detail = [{"loc": ["body", *field.split(".")], "msg": msg}
                      for field, msg in exc.errors.items()]
        else:
            detail = exc.message
        return JSONResponse({"detail": detail}, status_code=exc.status_code)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError):
        detail = [{"loc": list(e["loc"]), "msg": translate(e)} for e in exc.errors()]
        return JSONResponse({"detail": detail}, status_code=422)

    # 下面两个是数据库约束挡下来的。正常情况下 service 已经先检查过，
    # 走到这里说明是并发（两人同时操作）或者 service 漏了检查。
    @app.exception_handler(pg_errors.UniqueViolation)
    async def unique_violation(request: Request, exc: pg_errors.UniqueViolation):
        return JSONResponse({"detail": "单据已被他人处理，请刷新后再操作"}, status_code=409)

    @app.exception_handler(pg_errors.CheckViolation)
    async def check_violation(request: Request, exc: pg_errors.CheckViolation):
        return JSONResponse({"detail": "数据不符合要求"}, status_code=422)
