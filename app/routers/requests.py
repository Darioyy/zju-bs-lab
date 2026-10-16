from fastapi import APIRouter

from ..deps import Conn, CurrentUser
from ..schemas import DecisionIn, RequestCreate, RequestEdit, VersionIn
from ..services import requests as service

router = APIRouter(prefix="/requests", tags=["申请单"])


@router.get("")
def list_mine(conn: Conn, user: CurrentUser, status: str | None = None):
    """我的申请，可按状态筛选。"""
    return service.list_mine(conn, user, status)


@router.get("/todo")
def list_todo(conn: Conn, user: CurrentUser):
    """待我审批。"""
    return service.list_todo(conn, user)


@router.post("", status_code=201)
def create(body: RequestCreate, conn: Conn, user: CurrentUser):
    """新建草稿。"""
    return {"id": service.create(conn, user, body)}


@router.get("/{request_id}")
def get_detail(request_id: int, conn: Conn, user: CurrentUser):
    return service.get_detail(conn, user, request_id)


@router.put("/{request_id}")
def update(request_id: int, body: RequestEdit, conn: Conn, user: CurrentUser):
    """修改草稿。"""
    return service.update(conn, user, request_id, body)


@router.delete("/{request_id}", status_code=204)
def delete(request_id: int, version: int, conn: Conn, user: CurrentUser):
    service.delete(conn, user, request_id, version)


@router.post("/{request_id}/submit")
def submit(request_id: int, body: VersionIn, conn: Conn, user: CurrentUser):
    return service.change_status(conn, user, request_id, body.version, "submit")


@router.post("/{request_id}/withdraw")
def withdraw(request_id: int, body: VersionIn, conn: Conn, user: CurrentUser):
    return service.change_status(conn, user, request_id, body.version, "withdraw")


@router.post("/{request_id}/reopen")
def reopen(request_id: int, body: VersionIn, conn: Conn, user: CurrentUser):
    """被驳回的单子改回草稿，修改后重新提交。"""
    return service.change_status(conn, user, request_id, body.version, "reopen")


@router.post("/{request_id}/approve")
def approve(request_id: int, body: DecisionIn, conn: Conn, user: CurrentUser):
    return service.decide(conn, user, request_id, body.version, "approve", body.comment)


@router.post("/{request_id}/reject")
def reject(request_id: int, body: DecisionIn, conn: Conn, user: CurrentUser):
    return service.decide(conn, user, request_id, body.version, "reject", body.comment)
