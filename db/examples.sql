-- 各个页面要用到的查询，在 seed.sql 的数据上试过之后再搬进后端
-- psql 里可以 \set uid 5 切换“当前用户”，再执行下面的语句


-- 我的申请（陈杰）
\set uid 5

SELECT r.id, r.type, r.title, r.status, r.current_step, r.total_steps, r.updated_at
FROM requests r
WHERE r.applicant_id = :uid
ORDER BY r.created_at DESC;


-- 待我审批
-- 第 1 级：我是申请人所在部门的经理；第 2 级：我是财务；管理员两级都能审。都要排除自己的单子。
\set uid 2

SELECT r.id, r.type, r.title, u.display_name AS applicant, r.current_step, r.submitted_at
FROM requests r
JOIN users u ON u.id = r.applicant_id
JOIN departments d ON d.id = r.department_id
JOIN users me ON me.id = :uid
WHERE r.status = 'pending'
  AND r.applicant_id <> me.id
  AND (me.role = 'admin'
       OR (r.current_step = 1 AND d.manager_id = me.id)
       OR (r.current_step = 2 AND me.role = 'finance'))
ORDER BY r.submitted_at;

-- 换成管理员看一下：应该能看到张伟自己的那张请假（5 号）
\set uid 1
-- （重新执行上面那条查询）


-- 单据详情：主表 + 明细 + 审批历史
\set rid 2

SELECT r.*, e.category, e.amount, e.reason
FROM requests r
JOIN expense_details e ON e.request_id = r.id
WHERE r.id = :rid;

SELECT a.round, a.step, u.display_name AS approver, a.decision, a.comment, a.created_at
FROM approvals a
JOIN users u ON u.id = a.approver_id
WHERE a.request_id = :rid
ORDER BY a.round, a.step;


-- 审批通过（2 号单，财务王芳审第 2 级），放在事务里
-- 页面上看到的版本号是 3。UPDATE 带上 version = 3：
-- 别人先审了，version 已经变了，这条更新 0 行，就不往下写审批记录，回滚并返回 409。
BEGIN;

UPDATE requests
SET status       = CASE WHEN current_step = total_steps THEN 'approved' ELSE 'pending' END,
    current_step = CASE WHEN current_step = total_steps THEN NULL ELSE current_step + 1 END,
    finished_at  = CASE WHEN current_step = total_steps THEN now() END,
    version      = version + 1,
    updated_at   = now()
WHERE id = 2 AND version = 3 AND status = 'pending' AND current_step = 2
RETURNING id, status, current_step, version;

INSERT INTO approvals (request_id, round, step, approver_id, decision)
VALUES (2, 1, 2, 4, 'approve');

ROLLBACK;  -- 只是演示，不真的改；想保留就换成 COMMIT


-- 这些操作数据库会直接拒绝（每条单独执行，都应该报错）
-- 驳回不写理由
INSERT INTO approvals (request_id, round, step, approver_id, decision) VALUES (1, 1, 1, 2, 'reject');
-- 同一轮同一级审两次（2 号单第 1 级已经有记录了）
INSERT INTO approvals (request_id, round, step, approver_id, decision) VALUES (2, 1, 1, 1, 'approve');
-- 请假天数超过日期跨度
UPDATE leave_details SET days = 3 WHERE request_id = 1;
-- 审批中却没有当前级
UPDATE requests SET current_step = NULL WHERE id = 1;
