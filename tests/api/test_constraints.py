"""数据库约束的测试：绕过后端直接写库，这些语句都应该被 PostgreSQL 拒绝。

正常情况下后端会先检查，走不到数据库这一步；约束是最后一道防线。
db/examples.sql 末尾的几条语句就是这里的前四个用例。
"""

import uuid

import pytest
from psycopg import errors

CASES = [
    # 驳回不写理由
    ("INSERT INTO approvals (request_id, round, step, approver_id, decision) "
     "VALUES (1, 1, 1, 2, 'reject')", errors.CheckViolation),
    # 同一轮同一级审两次（2 号单第 1 级已经有记录）
    ("INSERT INTO approvals (request_id, round, step, approver_id, decision) "
     "VALUES (2, 1, 1, 1, 'approve')", errors.UniqueViolation),
    # 请假天数超过日期跨度（1 号单是 12 日到 13 日）
    ("UPDATE leave_details SET days = 3 WHERE request_id = 1", errors.CheckViolation),
    # 审批中却没有当前级
    ("UPDATE requests SET current_step = NULL WHERE id = 1", errors.CheckViolation),
    # 当前级超过总级数
    ("UPDATE requests SET current_step = 2 WHERE id = 1", errors.CheckViolation),
    # 不认识的状态
    ("UPDATE requests SET status = 'done' WHERE id = 1", errors.CheckViolation),
    # 请假天数不是半天的倍数
    ("UPDATE leave_details SET days = 1.3 WHERE request_id = 1", errors.CheckViolation),
    # 结束日期早于开始日期
    ("UPDATE leave_details SET end_date = '2026-10-11' WHERE request_id = 1", errors.CheckViolation),
    # 报销金额超过上限、不是正数
    ("UPDATE expense_details SET amount = 100000.01 WHERE request_id = 2", errors.CheckViolation),
    ("UPDATE expense_details SET amount = 0 WHERE request_id = 2", errors.CheckViolation),
    # 标题全是空格
    ("UPDATE requests SET title = '   ' WHERE id = 1", errors.CheckViolation),
    # 普通员工必须有部门
    ("UPDATE users SET department_id = NULL WHERE id = 5", errors.CheckViolation),
    # 用户名格式
    ("UPDATE users SET username = 'Chen Jie' WHERE id = 5", errors.CheckViolation),
    # 用户名重复
    ("UPDATE users SET username = 'zhangwei' WHERE id = 5", errors.UniqueViolation),
    # 部门重名
    ("UPDATE departments SET name = '技术部' WHERE id = 2", errors.UniqueViolation),
    # 审批人不存在
    ("INSERT INTO approvals (request_id, round, step, approver_id, decision) "
     "VALUES (1, 1, 1, 999, 'approve')", errors.ForeignKeyViolation),
]


@pytest.mark.parametrize("statement, error", CASES)
def test_rejected_by_database(db, statement, error):
    with pytest.raises(error):
        db.execute(statement)


def test_same_client_key_twice(db):
    key = uuid.uuid4()
    insert = ("INSERT INTO requests (type, title, applicant_id, department_id, client_key) "
              "VALUES ('leave', '测试', 5, 1, %s)")
    db.execute(insert, (key,))
    with pytest.raises(errors.UniqueViolation):
        db.execute(insert, (key,))
    # 换一个人用同一个 key 没问题，唯一约束是 (applicant_id, client_key)
    db.execute(insert.replace("5, 1", "6, 2"), (key,))


def test_failed_statement_changes_nothing(db):
    # 事务里第二条失败，第一条也要撤销
    with pytest.raises(errors.CheckViolation):
        with db.transaction():
            db.execute("UPDATE requests SET status = 'approved', current_step = NULL WHERE id = 1")
            db.execute("INSERT INTO approvals (request_id, round, step, approver_id, decision) "
                       "VALUES (1, 1, 1, 2, 'reject')")
    row = db.execute("SELECT status, current_step FROM requests WHERE id = 1").fetchone()
    assert row == {"status": "pending", "current_step": 1}
    assert db.execute("SELECT count(*) AS n FROM approvals WHERE request_id = 1").fetchone()["n"] == 0
