"""业务错误。

service 层发现问题就抛这里的异常，由 handlers.py 统一转成 HTTP 响应，
service 本身不用关心状态码和返回格式。
"""


class AppError(Exception):
    status_code = 400

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class Unauthorized(AppError):
    status_code = 401


class Forbidden(AppError):
    status_code = 403


class NotFound(AppError):
    status_code = 404


class Conflict(AppError):
    """状态不允许这个操作，或者单据已经被别人改过。"""

    status_code = 409


class Invalid(AppError):
    """输入格式没问题，但不符合业务规则，例如结束日期早于开始日期。

    errors 是 {字段: 原因}，字段名和前端表单的 name 一致，例如 "leave.end_date"。
    """

    status_code = 422

    def __init__(self, errors: dict[str, str]):
        super().__init__("输入有误")
        self.errors = errors
