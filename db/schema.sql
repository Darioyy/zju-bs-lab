-- 企业审批系统 数据库结构（PostgreSQL 13 及以上）
--
-- 用法：psql -U postgres -d approval -f db/schema.sql
-- 会先删掉同名的表再重建，表里原有的数据全部丢失，只在开发时用。

DROP TABLE IF EXISTS approvals, expense_details, leave_details, requests, sessions, users, departments CASCADE;


-- 部门 -----------------------------------------------------------------

CREATE TABLE departments (
    id          serial PRIMARY KEY,
    name        varchar(50) NOT NULL UNIQUE,
    manager_id  integer,                        -- 部门经理，外键在 users 建好后再加
    created_at  timestamptz NOT NULL DEFAULT now()
);


-- 用户 -----------------------------------------------------------------

CREATE TABLE users (
    id             serial PRIMARY KEY,
    username       varchar(32) NOT NULL UNIQUE,
    display_name   varchar(50) NOT NULL,
    password_hash  text NOT NULL,               -- pbkdf2_sha256$迭代次数$盐$哈希
    role           varchar(10) NOT NULL DEFAULT 'staff',
    department_id  integer REFERENCES departments (id),
    is_active      boolean NOT NULL DEFAULT true,
    created_at     timestamptz NOT NULL DEFAULT now(),

    CHECK (username ~ '^[a-z0-9_]{3,32}$'),
    CHECK (role IN ('staff', 'finance', 'admin')),
    CHECK (role = 'admin' OR department_id IS NOT NULL)
);

-- departments 和 users 互相引用，只能后加
ALTER TABLE departments
    ADD FOREIGN KEY (manager_id) REFERENCES users (id) ON DELETE SET NULL;


-- 登录会话 -------------------------------------------------------------
-- cookie 里放随机 token，库里只存它的 sha256，库泄露了也拿不到能用的 token

CREATE TABLE sessions (
    token_hash  char(64) PRIMARY KEY,
    user_id     integer NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    created_at  timestamptz NOT NULL DEFAULT now(),
    expires_at  timestamptz NOT NULL
);

CREATE INDEX ON sessions (user_id);
CREATE INDEX ON sessions (expires_at);


-- 申请单 ---------------------------------------------------------------
-- 请假和报销共用的部分放这里，各自特有的字段放 leave_details / expense_details

CREATE TABLE requests (
    id             serial PRIMARY KEY,
    type           varchar(10) NOT NULL,
    title          varchar(100) NOT NULL,
    applicant_id   integer NOT NULL REFERENCES users (id),
    department_id  integer NOT NULL REFERENCES departments (id),  -- 新建时申请人所在部门，之后调部门不影响这张单
    client_key     uuid NOT NULL,              -- 前端生成，防止重复提交建出两张单

    status         varchar(10) NOT NULL DEFAULT 'draft',
    round          smallint NOT NULL DEFAULT 0, -- 第几次提交，每次提交加 1
    total_steps    smallint,                    -- 提交时按类型确定：请假 1，报销 2
    current_step   smallint,                    -- 审批中时等第几级
    version        integer NOT NULL DEFAULT 1,  -- 每次修改加 1，用来发现并发修改

    created_at     timestamptz NOT NULL DEFAULT now(),
    updated_at     timestamptz NOT NULL DEFAULT now(),
    submitted_at   timestamptz,
    finished_at    timestamptz,                 -- 通过、驳回或撤回的时间

    UNIQUE (applicant_id, client_key),
    CHECK (type IN ('leave', 'expense')),
    CHECK (char_length(btrim(title)) >= 1),
    CHECK (status IN ('draft', 'pending', 'approved', 'rejected', 'withdrawn')),
    CHECK (total_steps IN (1, 2)),
    -- 审批中必须知道在第几级；NULL 参与比较结果是 NULL，CHECK 会放过，所以要写 IS NOT NULL
    CHECK (status <> 'pending' OR
           (total_steps IS NOT NULL AND current_step IS NOT NULL
            AND current_step BETWEEN 1 AND total_steps)),
    CHECK (status = 'draft' OR round >= 1)
);

CREATE INDEX ON requests (applicant_id, created_at DESC);
-- 待审批列表只查 pending 的单子，用部分索引
CREATE INDEX ON requests (current_step, department_id) WHERE status = 'pending';


CREATE TABLE leave_details (
    request_id  integer PRIMARY KEY REFERENCES requests (id) ON DELETE CASCADE,
    kind        varchar(10) NOT NULL,
    start_date  date NOT NULL,
    end_date    date NOT NULL,
    days        numeric(4, 1) NOT NULL,
    reason      text NOT NULL,

    CHECK (kind IN ('annual', 'sick', 'personal')),
    CHECK (end_date >= start_date),
    -- 以半天为单位，且不超过起止日期跨的天数（date 相减得到整数天）
    CHECK (days > 0 AND days * 2 = trunc(days * 2) AND days <= end_date - start_date + 1),
    CHECK (char_length(btrim(reason)) BETWEEN 1 AND 500)
);


CREATE TABLE expense_details (
    request_id  integer PRIMARY KEY REFERENCES requests (id) ON DELETE CASCADE,
    category    varchar(10) NOT NULL,
    amount      numeric(12, 2) NOT NULL,
    reason      text NOT NULL,

    CHECK (category IN ('travel', 'office', 'meal', 'other')),
    CHECK (amount > 0 AND amount <= 100000),
    CHECK (char_length(btrim(reason)) BETWEEN 1 AND 500)
);


-- 审批记录 -------------------------------------------------------------
-- 每一级的通过或驳回记一条。同一张单同一轮同一级只能有一条，
-- 两个人同时点通过时，就算应用层没拦住，第二条也插不进来。

CREATE TABLE approvals (
    id           serial PRIMARY KEY,
    request_id   integer NOT NULL REFERENCES requests (id) ON DELETE CASCADE,
    round        smallint NOT NULL,
    step         smallint NOT NULL,
    approver_id  integer NOT NULL REFERENCES users (id),
    decision     varchar(10) NOT NULL,
    comment      text NOT NULL DEFAULT '',
    created_at   timestamptz NOT NULL DEFAULT now(),

    UNIQUE (request_id, round, step),
    CHECK (decision IN ('approve', 'reject')),
    CHECK (decision <> 'reject' OR char_length(btrim(comment)) >= 1),  -- 驳回必须写理由
    CHECK (char_length(comment) <= 500)
);
