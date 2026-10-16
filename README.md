# 企业审批系统

B/S 体系软件设计课程大作业。员工在线提交请假、报销申请，部门经理和财务逐级审批。

需求、角色、状态和权限见 [docs/requirements.md](docs/requirements.md)。

## 技术栈

- 前端：原生 HTML、CSS、JavaScript，不用框架
- 后端：Python 3.10+，FastAPI
- 数据库：PostgreSQL 13+，不用 ORM，SQL 都写在 Repository 层（psycopg 3）
- 部署：Docker Compose

## 目录

```
app/
  main.py            入口，挂路由和静态页面
  config.py          配置（环境变量）
  db.py              连接池
  deps.py            依赖：数据库连接、当前登录用户
  schemas.py         请求体格式
  errors.py          业务错误
  handlers.py        错误转成 JSON 响应
  security.py        密码哈希、登录 token
  workflow.py        状态机和权限规则（纯函数）
  validation.py      跨字段校验
  routers/           路由层：HTTP 相关
  services/          业务层：检查状态和权限、管理事务
  repositories/      数据层：所有 SQL
static/              页面、js、css
db/
  schema.sql         建表
  seed.sql           演示数据
  examples.sql       页面要用的查询，以及数据库约束的验证
tests/               测试
docs/requirements.md 需求说明
```

一个请求经过的层次：

```
页面 fetch → routers（取参数）→ services（状态机、权限、事务）→ repositories（SQL）→ PostgreSQL
```

## 运行

1. 初始化数据库：

   ```bash
   createdb -U postgres approval
   psql -U postgres -d approval -f db/schema.sql
   psql -U postgres -d approval -f db/seed.sql
   ```

2. 装依赖，启动：

   ```bash
   python -m venv .venv
   .venv/bin/pip install -r requirements.txt        # Windows: .venv\Scripts\pip
   .venv/bin/uvicorn app.main:app --reload
   ```

   数据库地址默认是 `postgresql://postgres:postgres@localhost:5432/approval`，不一样就设环境变量 `DATABASE_URL`。

3. 浏览器打开 <http://127.0.0.1:8000>。接口文档在 <http://127.0.0.1:8000/docs>。

测试：`pip install pytest` 后在项目根目录运行 `pytest`。

演示账号的密码都是 `123456`：

| 账号 | 姓名 | 说明 |
|---|---|---|
| admin | 系统管理员 | 管理员 |
| zhangwei | 张伟 | 技术部经理 |
| lina | 李娜 | 市场部经理 |
| wangfang | 王芳 | 财务部经理，财务 |
| chenjie | 陈杰 | 技术部员工 |
| liuyang | 刘洋 | 市场部员工 |

## 接口

都在 `/api` 下，登录状态放在 HttpOnly cookie 里。

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/login` | 登录 |
| POST | `/logout` | 退出 |
| GET | `/me` | 当前用户 |
| GET | `/requests?status=` | 我的申请 |
| GET | `/requests/todo` | 待我审批 |
| POST | `/requests` | 新建草稿，带 `client_key` 防重复 |
| GET | `/requests/{id}` | 详情，含审批记录和当前用户能做的操作 |
| PUT | `/requests/{id}` | 修改草稿 |
| DELETE | `/requests/{id}?version=` | 删除草稿 |
| POST | `/requests/{id}/submit` | 提交 |
| POST | `/requests/{id}/withdraw` | 撤回 |
| POST | `/requests/{id}/reopen` | 被驳回后改回草稿 |
| POST | `/requests/{id}/approve` | 通过当前一级 |
| POST | `/requests/{id}/reject` | 驳回，必须写理由 |

修改类的操作都要带上页面看到的 `version`，单子已经被别人改过时返回 409。

## 进度

- [x] 需求与数据模型
- [ ] 首个完整功能：登录、提交、审批通过或驳回
- [ ] 测试与部署
- [ ] 最终演示
