"""管理部门和用户的规则测试，不需要数据库。"""

from app.accounts import deactivate_error, manager_error, user_errors

ADMIN = {"id": 1, "role": "admin", "display_name": "系统管理员"}
ZHANGWEI = {"id": 2, "role": "staff", "display_name": "张伟", "department_id": 1, "is_active": True}
CHENJIE = {"id": 5, "role": "staff", "display_name": "陈杰", "department_id": 1, "is_active": True}
TECH = {"id": 1, "name": "技术部", "manager_id": 2}
MARKET = {"id": 2, "name": "市场部", "manager_id": 3}


def test_staff_and_finance_need_department():
    assert user_errors(ADMIN, "staff", None) == {"department_id": "普通员工和财务必须属于一个部门"}
    assert "department_id" in user_errors(ADMIN, "finance", None)
    assert user_errors(ADMIN, "admin", None) == {}
    assert user_errors(ADMIN, "staff", 1) == {}


def test_admin_cannot_demote_self():
    assert user_errors(ADMIN, "staff", 1, target=ADMIN) == {"role": "不能取消自己的管理员身份"}
    assert user_errors(ADMIN, "admin", None, target=ADMIN) == {}
    # 改别的管理员可以
    other_admin = {"id": 7, "role": "admin", "display_name": "副管理员"}
    assert user_errors(ADMIN, "staff", 1, target=other_admin) == {}


def test_manager_cannot_move_out():
    errors = user_errors(ADMIN, "staff", 2, target=ZHANGWEI, managed=TECH)
    assert errors == {"department_id": "张伟是技术部的经理，要先给技术部换经理"}
    # 部门不变，改角色可以
    assert user_errors(ADMIN, "finance", 1, target=ZHANGWEI, managed=TECH) == {}
    assert "department_id" in user_errors(ADMIN, "admin", None, target=ZHANGWEI, managed=TECH)


def test_deactivate():
    assert deactivate_error(ADMIN, ADMIN, None) == "不能停用自己"
    assert deactivate_error(ADMIN, ZHANGWEI, TECH) == "张伟是技术部的经理，要先给技术部换经理"
    assert deactivate_error(ADMIN, CHENJIE, None) is None


def test_manager_candidate():
    assert manager_error(TECH, CHENJIE) is None
    assert manager_error(TECH, None) == "没有这个用户"
    assert manager_error(MARKET, CHENJIE) == "陈杰不是市场部的人，要先调到市场部"
    assert manager_error(TECH, {**CHENJIE, "is_active": False}) == "陈杰已停用"
