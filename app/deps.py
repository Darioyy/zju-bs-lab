"""路由共用的依赖：数据库连接、当前登录用户。"""

from typing import Annotated

from fastapi import Cookie, Depends

from . import security
from .db import Connection, get_conn
from .errors import Forbidden, Unauthorized
from .repositories import sessions

SESSION_COOKIE = "session"

Conn = Annotated[Connection, Depends(get_conn)]


def current_user(conn: Conn, session: Annotated[str | None, Cookie()] = None) -> dict:
    """从 cookie 里的 token 找到登录用户，找不到就是 401。"""
    if not session:
        raise Unauthorized("请先登录")
    user = sessions.get_user(conn, security.token_hash(session))
    if user is None:
        raise Unauthorized("登录已过期，请重新登录")
    return user


CurrentUser = Annotated[dict, Depends(current_user)]


def admin_user(user: CurrentUser) -> dict:
    """管理接口用：不是管理员就是 403。"""
    if user["role"] != "admin":
        raise Forbidden("只有管理员能管理部门和用户")
    return user


AdminUser = Annotated[dict, Depends(admin_user)]
