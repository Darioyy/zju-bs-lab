"""状态机和权限规则的测试，不需要数据库。"""

from datetime import datetime, timezone

import pytest

from app.errors import Conflict
from app.workflow import (allowed_actions, can_approve, can_view, check_status,
                          transition)

NOW = datetime(2026, 10, 9, 12, 0, tzinfo=timezone.utc)

# 部门：技术部，经理 id=2。财务 id=4，管理员 id=1，普通员工 id=5、6
ADMIN = {"id": 1, "role": "admin"}
MANAGER = {"id": 2, "role": "staff"}
FINANCE = {"id": 4, "role": "finance"}
STAFF = {"id": 5, "role": "staff"}
OTHER = {"id": 6, "role": "staff"}


def make_request(**kw):
    req = {"id": 1, "type": "expense", "applicant_id": 5, "manager_id": 2,
           "status": "pending", "round": 1, "total_steps": 2, "current_step": 1}
    req.update(kw)
    return req


# 状态机 ----------------------------------------------------------------

def test_submit_starts_from_step_one():
    req = make_request(type="leave", status="draft", round=0, total_steps=None, current_step=None)
    changes = transition(req, "submit", NOW)
    assert changes["status"] == "pending"
    assert changes["round"] == 1
    assert changes["total_steps"] == 1
    assert changes["current_step"] == 1


def test_expense_needs_two_steps():
    req = make_request(status="draft", round=0, total_steps=None, current_step=None)
    assert transition(req, "submit", NOW)["total_steps"] == 2


def test_approve_moves_to_next_step():
    assert transition(make_request(current_step=1), "approve", NOW) == {"current_step": 2}


def test_approve_last_step_finishes():
    changes = transition(make_request(current_step=2), "approve", NOW)
    assert changes == {"status": "approved", "current_step": None, "finished_at": NOW}


def test_resubmit_after_reject_starts_new_round():
    req = make_request(status="draft", round=1, current_step=None)
    changes = transition(req, "submit", NOW)
    assert changes["round"] == 2
    assert changes["current_step"] == 1


@pytest.mark.parametrize("status, action", [
    ("approved", "reject"),
    ("approved", "withdraw"),
    ("draft", "approve"),
    ("rejected", "approve"),
    ("pending", "edit"),
    ("pending", "submit"),
    ("withdrawn", "submit"),
    ("withdrawn", "reopen"),
])
def test_illegal_transitions_are_rejected(status, action):
    with pytest.raises(Conflict):
        check_status(make_request(status=status), action)


# 谁能审批 --------------------------------------------------------------

def test_manager_approves_step_one():
    assert can_approve(MANAGER, make_request(current_step=1))


def test_finance_cannot_approve_step_one():
    assert not can_approve(FINANCE, make_request(current_step=1))


def test_finance_approves_step_two():
    assert can_approve(FINANCE, make_request(current_step=2))


def test_manager_cannot_approve_step_two():
    assert not can_approve(MANAGER, make_request(current_step=2))


def test_cannot_approve_own_request():
    # 经理自己请假，第 1 级的审批人按规则是他自己
    req = make_request(type="leave", applicant_id=2, total_steps=1)
    assert not can_approve(MANAGER, req)
    assert can_approve(ADMIN, req)


def test_finance_cannot_approve_own_expense():
    assert not can_approve(FINANCE, make_request(applicant_id=4, current_step=2))


def test_nobody_approves_finished_request():
    req = make_request(status="approved", current_step=None)
    assert not can_approve(ADMIN, req)
    assert not can_approve(MANAGER, req)


# 谁能看 ----------------------------------------------------------------

def test_draft_only_visible_to_applicant():
    req = make_request(status="draft", current_step=None)
    assert can_view(STAFF, req)
    assert not can_view(MANAGER, req)
    assert not can_view(ADMIN, req)


def test_other_staff_cannot_view():
    assert not can_view(OTHER, make_request())


def test_finance_sees_expense_but_not_leave():
    assert can_view(FINANCE, make_request(type="expense"))
    assert not can_view(FINANCE, make_request(type="leave", total_steps=1))


# 详情页按钮 ------------------------------------------------------------

def test_actions_for_applicant():
    assert allowed_actions(STAFF, make_request(status="draft", current_step=None)) == ["edit", "delete", "submit"]
    assert allowed_actions(STAFF, make_request(status="pending")) == ["withdraw"]
    assert allowed_actions(STAFF, make_request(status="rejected", current_step=None)) == ["reopen"]
    assert allowed_actions(STAFF, make_request(status="approved", current_step=None)) == []


def test_actions_for_approver():
    assert allowed_actions(MANAGER, make_request(current_step=1)) == ["approve", "reject"]
    assert allowed_actions(MANAGER, make_request(current_step=2)) == []
