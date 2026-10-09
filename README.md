# 企业审批系统

B/S 体系软件设计课程大作业。员工在线提交请假、报销申请，部门经理和财务逐级审批。

需求、角色、状态和权限见 [docs/requirements.md](docs/requirements.md)。

## 技术栈

- 前端：原生 HTML、CSS、JavaScript
- 后端：Python，FastAPI
- 数据库：PostgreSQL，不用 ORM，SQL 都写在 Repository 层
- 部署：Docker Compose

## 目录

```
docs/requirements.md   需求说明
db/schema.sql          建表
db/seed.sql            演示数据
db/examples.sql        页面要用的查询，以及数据库约束的验证
```

## 初始化数据库

需要 PostgreSQL 13 及以上（用到了内置的 `gen_random_uuid()`）。

```bash
createdb -U postgres approval
psql -U postgres -d approval -f db/schema.sql
psql -U postgres -d approval -f db/seed.sql
```

演示账号的密码都是 `123456`：

| 账号 | 姓名 | 说明 |
|---|---|---|
| admin | 系统管理员 | 管理员 |
| zhangwei | 张伟 | 技术部经理 |
| lina | 李娜 | 市场部经理 |
| wangfang | 王芳 | 财务部经理，财务 |
| chenjie | 陈杰 | 技术部员工 |
| liuyang | 刘洋 | 市场部员工 |

## 进度

- [x] 需求与数据模型
- [ ] 首个完整功能：登录、提交、审批通过或驳回
- [ ] 测试与部署
- [ ] 最终演示
