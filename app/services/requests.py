"""申请单的业务逻辑。

每个修改操作的检查顺序都一样：
1. 单据存在吗（404），当前用户看得到吗（403）
2. 当前状态允许这个操作吗（409）
3. 当前用户有资格做这个操作吗（403）
4. 写库时带上版本号，被别人抢先改过就失败（409）
"""

from psycopg import Connection

from .. import validation, workflow
from ..errors import Conflict, Forbidden, Invalid, NotFound
from ..repositories import approvals
from ..repositories import requests as repo
from ..schemas import RequestBody, RequestCreate, RequestEdit

DETAIL_NAME = {"leave": "请假", "expense": "报销"}


# 查询 ------------------------------------------------------------------

def list_mine(conn: Connection, user: dict, status: str | None) -> list[dict]:
    if status and status not in workflow.STATUS_TEXT:
        raise Invalid({"status": "没有这个状态"})
    return repo.list_by_applicant(conn, user["id"], status)


def list_todo(conn: Connection, user: dict) -> list[dict]:
    return repo.list_todo(conn, user)


def get_detail(conn: Connection, user: dict, request_id: int) -> dict:
    req = _load(conn, user, request_id)
    if req["type"] == "leave":
        req["leave"] = repo.get_leave(conn, request_id)
    else:
        req["expense"] = repo.get_expense(conn, request_id)
    req["approvals"] = approvals.list_by_request(conn, request_id)
    req["actions"] = workflow.allowed_actions(user, req)
    del req["client_key"]
    return req


# 申请人的操作 ----------------------------------------------------------

def create(conn: Connection, user: dict, data: RequestCreate) -> int:
    if user["department_id"] is None:
        raise Forbidden("管理员不属于任何部门，不能提交申请")
    _check_body(data.type, data)

    with conn.transaction():
        request_id = repo.insert(conn, user["id"], user["department_id"],
                                 data.type, data.title, data.client_key)
        if request_id is None:
            # 这个 client_key 已经建过单子了（重复提交），直接返回那一张
            return repo.find_by_client_key(conn, user["id"], data.client_key)
        _save_body(conn, request_id, data.type, data)
    return request_id


def update(conn: Connection, user: dict, request_id: int, data: RequestEdit) -> dict:
    req = _load(conn, user, request_id)
    workflow.check_status(req, "edit")
    _require_applicant(user, req, "edit")
    _check_body(req["type"], data)

    with conn.transaction():
        _save_fields(conn, req, data.version, {"title": data.title})
        _save_body(conn, request_id, req["type"], data)
    return get_detail(conn, user, request_id)


def delete(conn: Connection, user: dict, request_id: int, version: int) -> None:
    req = _load(conn, user, request_id)
    workflow.check_status(req, "delete")
    _require_applicant(user, req, "delete")
    if not repo.delete_draft(conn, request_id, version):
        raise Conflict("单据已被修改，请刷新后再操作")


def change_status(conn: Connection, user: dict, request_id: int,
                  version: int, action: str) -> dict:
    """提交、撤回、重新编辑。这三个操作只改状态，写法一样。"""
    req = _load(conn, user, request_id)
    workflow.check_status(req, action)
    _require_applicant(user, req, action)
    _save_fields(conn, req, version, workflow.transition(req, action))
    return get_detail(conn, user, request_id)


# 审批人的操作 ----------------------------------------------------------

def decide(conn: Connection, user: dict, request_id: int,
           version: int, decision: str, comment: str) -> dict:
    """通过或驳回当前这一级。decision 是 "approve" 或 "reject"。"""
    req = _load(conn, user, request_id)
    workflow.check_status(req, decision)
    if not workflow.can_approve(user, req):
        if workflow.is_applicant(user, req):
            raise Forbidden("不能审批自己的申请")
        raise Forbidden("你不是这一级的审批人")
    if decision == "reject" and not comment:
        raise Invalid({"comment": "驳回必须填写理由"})

    # 改单据状态和写审批记录要么都成功，要么都不做
    with conn.transaction():
        _save_fields(conn, req, version, workflow.transition(req, decision))
        approvals.insert(conn, request_id, req["round"], req["current_step"],
                         user["id"], decision, comment)
    return get_detail(conn, user, request_id)


# 内部函数 --------------------------------------------------------------

def _load(conn: Connection, user: dict, request_id: int) -> dict:
    req = repo.get(conn, request_id)
    if req is None:
        raise NotFound("单据不存在")
    if not workflow.can_view(user, req):
        raise Forbidden("没有权限查看这张单据")
    return req


def _require_applicant(user: dict, req: dict, action: str) -> None:
    if not workflow.is_applicant(user, req):
        raise Forbidden(f"只有申请人本人可以{workflow.ACTION_TEXT[action]}")


def _save_fields(conn: Connection, req: dict, version: int, changes: dict) -> None:
    if repo.update_fields(conn, req["id"], version, changes) is None:
        raise Conflict("单据已被修改，请刷新后再操作")


def _check_body(type_: str, data: RequestBody) -> None:
    """单据类型和明细要对得上，再检查跨字段的规则。"""
    detail = getattr(data, type_)
    if detail is None:
        raise Invalid({type_: f"请填写{DETAIL_NAME[type_]}信息"})
    other = "expense" if type_ == "leave" else "leave"
    if getattr(data, other) is not None:
        raise Invalid({other: f"{DETAIL_NAME[type_]}单不能带{DETAIL_NAME[other]}信息"})
    if type_ == "leave":
        errors = validation.leave_errors(detail.start_date, detail.end_date, detail.days)
        if errors:
            raise Invalid({f"leave.{field}": msg for field, msg in errors.items()})


def _save_body(conn: Connection, request_id: int, type_: str, data: RequestBody) -> None:
    if type_ == "leave":
        repo.save_leave(conn, request_id, data.leave)
    else:
        repo.save_expense(conn, request_id, data.expense)
