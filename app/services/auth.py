from psycopg import Connection

from .. import config, security
from ..errors import Unauthorized
from ..repositories import sessions, users

# 用户名不存在时也算一次哈希，让两种失败的耗时差不多，
# 别人就没法靠响应快慢判断某个用户名存不存在
DUMMY_HASH = security.hash_password("dummy")


def public(user: dict) -> dict:
    """返回给前端的用户信息，不带密码哈希。"""
    return {k: user[k] for k in ("id", "username", "display_name", "role", "department_id")}


def login(conn: Connection, username: str, password: str) -> tuple[dict, str]:
    user = users.get_by_username(conn, username)
    if user is None:
        security.verify_password(password, DUMMY_HASH)
        raise Unauthorized("用户名或密码错误")
    if not security.verify_password(password, user["password_hash"]) or not user["is_active"]:
        raise Unauthorized("用户名或密码错误")

    token = security.new_token()
    with conn.transaction():
        sessions.delete_expired(conn, user["id"])
        sessions.create(conn, security.token_hash(token), user["id"], config.SESSION_HOURS)
    return public(user), token


def logout(conn: Connection, token: str) -> None:
    sessions.delete(conn, security.token_hash(token))
