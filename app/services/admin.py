"""管理部门和用户。调用这里的函数前，路由已经确认当前用户是管理员（deps.AdminUser）。

规则本身在 accounts.py 里，这里负责查出规则要用的数据、抛出对应的错误、写库。
"""

from psycopg import Connection
from psycopg import errors as pg_errors

from .. import accounts, security
from ..errors import Conflict, Invalid, NotFound
from ..repositories import departments, sessions, users
from ..schemas import DepartmentEdit, UserCreate, UserEdit


# 部门 ------------------------------------------------------------------

def list_departments(conn: Connection) -> list[dict]:
    return departments.list_all(conn)


def create_department(conn: Connection, name: str) -> int:
    """新部门还没有人，经理等调人进来以后再指定。"""
    try:
        return departments.insert(conn, name)
    except pg_errors.UniqueViolation:
        raise Invalid({"name": "已经有同名的部门"}) from None


def update_department(conn: Connection, department_id: int, data: DepartmentEdit) -> None:
    dept = departments.get(conn, department_id)
    if dept is None:
        raise NotFound("部门不存在")
    if data.manager_id is not None:
        error = accounts.manager_error(dept, users.get(conn, data.manager_id))
        if error:
            raise Invalid({"manager_id": error})
    # 换经理以后，这个部门审批中、停在第 1 级的单子自动改由新经理审：
    # 审批人是审批时按 departments.manager_id 查的，不是提交时记下来的
    try:
        departments.update(conn, department_id, data.name, data.manager_id)
    except pg_errors.UniqueViolation:
        raise Invalid({"name": "已经有同名的部门"}) from None


# 用户 ------------------------------------------------------------------

def list_users(conn: Connection) -> list[dict]:
    return users.list_all(conn)


def create_user(conn: Connection, admin: dict, data: UserCreate) -> int:
    _check_user(conn, admin, data)
    if users.get_by_username(conn, data.username) is not None:
        raise Invalid({"username": "用户名已存在"})
    try:
        return users.insert(conn, data.username, data.display_name,
                            security.hash_password(data.password),
                            data.role, data.department_id)
    except pg_errors.UniqueViolation:
        # 上面查过不存在，两个请求同时建同一个用户名时才会走到这里
        raise Invalid({"username": "用户名已存在"}) from None


def update_user(conn: Connection, admin: dict, user_id: int, data: UserEdit) -> None:
    target = _get_user(conn, user_id)
    _check_user(conn, admin, data, target)
    users.update(conn, user_id, data.display_name, data.role, data.department_id)


def set_active(conn: Connection, admin: dict, user_id: int, active: bool) -> None:
    """停用或启用。停用只做标记不删记录，审批记录里还要显示这个人的名字。"""
    target = _get_user(conn, user_id)
    if not active:
        error = accounts.deactivate_error(admin, target, departments.managed_by(conn, user_id))
        if error:
            raise Conflict(error)
    with conn.transaction():
        users.set_active(conn, user_id, active)
        if not active:
            sessions.delete_by_user(conn, user_id)


def reset_password(conn: Connection, user_id: int, password: str) -> None:
    """重置后原来登录的地方都要重新登录。"""
    _get_user(conn, user_id)
    with conn.transaction():
        users.set_password(conn, user_id, security.hash_password(password))
        sessions.delete_by_user(conn, user_id)


# 内部函数 --------------------------------------------------------------

def _get_user(conn: Connection, user_id: int) -> dict:
    user = users.get(conn, user_id)
    if user is None:
        raise NotFound("用户不存在")
    return user


def _check_user(conn: Connection, admin: dict, data: UserEdit, target: dict | None = None) -> None:
    managed = departments.managed_by(conn, target["id"]) if target else None
    errors = accounts.user_errors(admin, data.role, data.department_id, target, managed)
    if data.department_id is not None and departments.get(conn, data.department_id) is None:
        errors["department_id"] = "部门不存在"
    if errors:
        raise Invalid(errors)
