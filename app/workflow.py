"""审批流程：状态机、走几级、谁能做什么。

这里只有纯函数，不碰数据库和 HTTP，可以单独测试。
user 和 req 都是字典，键名和数据库列名一致；req 还要带上 manager_id
（申请人所在部门的经理），由 repositories/requests.py 查询时一起取出。
"""

from datetime import datetime, timezone

from .errors import Conflict

# 提交时按类型确定走几级
STEPS = {"leave": 1, "expense": 2}

STATUS_TEXT = {
    "draft": "草稿",
    "pending": "审批中",
    "approved": "已通过",
    "rejected": "已驳回",
    "withdrawn": "已撤回",
}

ACTION_TEXT = {
    "edit": "修改",
    "delete": "删除",
    "submit": "提交",
    "withdraw": "撤回",
    "reopen": "重新编辑",
    "approve": "通过",
    "reject": "驳回",
}

# 每个操作只能在这些状态下做，对应 docs/requirements.md 3.1 的状态图
ALLOWED_FROM = {
    "edit": {"draft"},
    "delete": {"draft"},
    "submit": {"draft"},
    "withdraw": {"pending"},
    "reopen": {"rejected"},
    "approve": {"pending"},
    "reject": {"pending"},
}

APPLICANT_ACTIONS = ("edit", "delete", "submit", "withdraw", "reopen")


def check_status(req: dict, action: str) -> None:
    if req["status"] not in ALLOWED_FROM[action]:
        status = STATUS_TEXT[req["status"]]
        raise Conflict(f"单据当前是“{status}”，不能{ACTION_TEXT[action]}")


def transition(req: dict, action: str, now: datetime | None = None) -> dict:
    """返回这次操作要写回 requests 表的字段。调用前先 check_status。"""
    now = now or datetime.now(timezone.utc)

    if action == "submit":
        return {
            "status": "pending",
            "round": req["round"] + 1,
            "total_steps": STEPS[req["type"]],
            "current_step": 1,
            "submitted_at": now,
            "finished_at": None,
        }
    if action == "approve":
        if req["current_step"] < req["total_steps"]:
            return {"current_step": req["current_step"] + 1}
        return {"status": "approved", "current_step": None, "finished_at": now}
    if action == "reject":
        return {"status": "rejected", "current_step": None, "finished_at": now}
    if action == "withdraw":
        return {"status": "withdrawn", "current_step": None, "finished_at": now}
    if action == "reopen":
        return {"status": "draft", "finished_at": None}
    raise ValueError(f"未知操作 {action}")


def is_applicant(user: dict, req: dict) -> bool:
    return user["id"] == req["applicant_id"]


def can_approve(user: dict, req: dict) -> bool:
    """user 能不能审当前这一级。"""
    if req["status"] != "pending" or is_applicant(user, req):
        return False
    if user["role"] == "admin":
        return True
    if req["current_step"] == 1:
        return user["id"] == req["manager_id"]
    if req["current_step"] == 2:
        return user["role"] == "finance"
    return False


def can_view(user: dict, req: dict) -> bool:
    if is_applicant(user, req):
        return True
    if req["status"] == "draft":
        return False
    if user["role"] == "admin" or user["id"] == req["manager_id"]:
        return True
    return req["type"] == "expense" and user["role"] == "finance"


def allowed_actions(user: dict, req: dict) -> list[str]:
    """详情页显示哪些按钮。后端每个操作还会再检查一遍，这里只管显示。"""
    actions = []
    if is_applicant(user, req):
        actions += [a for a in APPLICANT_ACTIONS if req["status"] in ALLOWED_FROM[a]]
    if can_approve(user, req):
        actions += ["approve", "reject"]
    return actions
