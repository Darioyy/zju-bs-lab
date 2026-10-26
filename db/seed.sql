-- 演示数据，在 schema.sql 之后执行：psql -U postgres -d approval -f db/seed.sql
-- 所有账号的密码都是 123456

-- 下面写的时间都是北京时间。不设的话按数据库的时区理解，Docker 里的数据库是 UTC，页面上会差 8 小时
SET TIME ZONE 'Asia/Shanghai';

INSERT INTO departments (id, name) VALUES
    (1, '技术部'),
    (2, '市场部'),
    (3, '财务部');

INSERT INTO users (id, username, display_name, password_hash, role, department_id) VALUES
    (1, 'admin',    '系统管理员', 'pbkdf2_sha256$260000$7NkVpZOjhpLIHpKZ7taSTw==$OPCAtOd/V4BOlZtx6iaAhgHRc1ftTPV+LM6oGklF1f4=', 'admin',   NULL),
    (2, 'zhangwei', '张伟',       'pbkdf2_sha256$260000$AGnApMkJj0JGLb8Aavtz5g==$R+JZPCJhXKwZuzK6nqoBSc/c695YEOzg9c7svJtlvMA=', 'staff',   1),
    (3, 'lina',     '李娜',       'pbkdf2_sha256$260000$pw0Wyx3vTaBQs/e30w4/+A==$E3Z5RcqfJsR/xRvnKDejG6vdvs9JdkuDEk04eL2xCz0=', 'staff',   2),
    (4, 'wangfang', '王芳',       'pbkdf2_sha256$260000$8IeGvPtw+d8e6e1Mbf7Rng==$2u/bsYRpM59dRO3Hf5xmk0rg7QGw+gbV8ZrsLoqm1Qs=', 'finance', 3),
    (5, 'chenjie',  '陈杰',       'pbkdf2_sha256$260000$bHx42ncGqUjCEH1Y9+j1ng==$kN7jmwgQI0PHpgqmeKUDzzDFFRxF+SAaj5oMgoDvVJU=', 'staff',   1),
    (6, 'liuyang',  '刘洋',       'pbkdf2_sha256$260000$gOvWYoeRlG8RWL5RbZevJA==$0uj2bkrrwzeh/CVguZ91KHUa3p8WQzO/2hr5bZyiL8c=', 'staff',   2);

UPDATE departments SET manager_id = 2 WHERE id = 1;  -- 张伟 管技术部
UPDATE departments SET manager_id = 3 WHERE id = 2;  -- 李娜 管市场部
UPDATE departments SET manager_id = 4 WHERE id = 3;  -- 王芳 管财务部，同时是财务


-- 几张不同状态的单子，方便看页面效果
--   1 陈杰 请假 审批中，等张伟
--   2 陈杰 报销 张伟已通过，等财务
--   3 刘洋 报销 被李娜驳回
--   4 刘洋 请假 已通过
--   5 张伟 请假 审批中，他自己是经理，等管理员
--   6 陈杰 报销 草稿

INSERT INTO requests (id, type, title, applicant_id, department_id, client_key,
                      status, round, total_steps, current_step, version,
                      created_at, updated_at, submitted_at, finished_at) VALUES
    (1, 'leave',   '国庆后补休两天',     5, 1, gen_random_uuid(), 'pending',  1, 1, 1,    2,
        '2026-10-08 09:10', '2026-10-08 09:12', '2026-10-08 09:12', NULL),
    (2, 'expense', '杭州出差交通费',     5, 1, gen_random_uuid(), 'pending',  1, 2, 2,    3,
        '2026-10-06 14:00', '2026-10-07 10:30', '2026-10-06 14:05', NULL),
    (3, 'expense', '客户招待餐费',       6, 2, gen_random_uuid(), 'rejected', 1, 2, NULL, 3,
        '2026-10-05 18:20', '2026-10-06 09:00', '2026-10-05 18:25', '2026-10-06 09:00'),
    (4, 'leave',   '病假一天',           6, 2, gen_random_uuid(), 'approved', 1, 1, NULL, 3,
        '2026-09-28 08:00', '2026-09-28 09:15', '2026-09-28 08:01', '2026-09-28 09:15'),
    (5, 'leave',   '年假',               2, 1, gen_random_uuid(), 'pending',  1, 1, 1,    2,
        '2026-10-08 16:00', '2026-10-08 16:01', '2026-10-08 16:01', NULL),
    (6, 'expense', '买显示器支架',       5, 1, gen_random_uuid(), 'draft',    0, NULL, NULL, 1,
        '2026-10-09 08:40', '2026-10-09 08:40', NULL, NULL);

INSERT INTO leave_details (request_id, kind, start_date, end_date, days, reason) VALUES
    (1, 'personal', '2026-10-12', '2026-10-13', 2,   '家里有事'),
    (4, 'sick',     '2026-09-28', '2026-09-28', 1,   '发烧，已去医院'),
    (5, 'annual',   '2026-10-20', '2026-10-22', 2.5, '回老家，22 日下午回来上班');

INSERT INTO expense_details (request_id, category, amount, reason) VALUES
    (2, 'travel', 386.50, '10 月 3 日到 5 日去杭州见客户，高铁往返'),
    (3, 'meal',   2680.00, '招待客户晚餐'),
    (6, 'office', 129.00, '工位显示器太矮，买个支架');

INSERT INTO approvals (request_id, round, step, approver_id, decision, comment, created_at) VALUES
    (2, 1, 1, 2, 'approve', '',                            '2026-10-07 10:30'),
    (3, 1, 1, 3, 'reject',  '超出招待标准，请附上客户名单', '2026-10-06 09:00'),
    (4, 1, 1, 3, 'approve', '注意休息',                    '2026-09-28 09:15');


-- 上面手动指定了 id，要把序列拨到最大值之后，否则下次自动生成的 id 会冲突
SELECT setval('departments_id_seq', (SELECT max(id) FROM departments));
SELECT setval('users_id_seq',       (SELECT max(id) FROM users));
SELECT setval('requests_id_seq',    (SELECT max(id) FROM requests));
