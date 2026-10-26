"""申请单接口的测试：完整流程，以及 401、403、404、409、422 各类错误。

演示数据见 db/seed.sql：
  1 陈杰 请假 等张伟（第 1 级）      2 陈杰 报销 等财务（第 2 级）
  3 刘洋 报销 被驳回                 4 刘洋 请假 已通过
  5 张伟 请假 等管理员               6 陈杰 报销 草稿
"""

import uuid

LEAVE = {
    "type": "leave",
    "title": "回家",
    "leave": {"kind": "annual", "start_date": "2026-11-02", "end_date": "2026-11-03",
              "days": "2", "reason": "家里有事"},
}
EXPENSE = {
    "type": "expense",
    "title": "打车",
    "expense": {"category": "travel", "amount": "56.50", "reason": "见客户"},
}


def new(c, body):
    """新建一张草稿，返回 id。"""
    r = c.post("/api/requests", json={**body, "client_key": str(uuid.uuid4())})
    assert r.status_code == 201, r.text
    return r.json()["id"]


def detail(c, request_id):
    r = c.get(f"/api/requests/{request_id}")
    assert r.status_code == 200, r.text
    return r.json()


def act(c, request_id, action, **body):
    """对单据做一个操作，版本号取当前最新的。"""
    version = detail(c, request_id)["version"]
    return c.post(f"/api/requests/{request_id}/{action}", json={"version": version, **body})


def fields(r):
    """422 响应里出错的字段，例如 {"leave.end_date", ...}。"""
    assert r.status_code == 422, r.text
    return {".".join(e["loc"][1:]) for e in r.json()["detail"]}


# 登录 ------------------------------------------------------------------

def test_login_and_me(client):
    c = client("chenjie")
    me = c.get("/api/me").json()
    assert me["display_name"] == "陈杰"
    assert "password_hash" not in me


def test_wrong_password(client):
    r = client().post("/api/login", json={"username": "chenjie", "password": "wrong"})
    assert r.status_code == 401
    r = client().post("/api/login", json={"username": "nobody", "password": "wrong"})
    assert r.status_code == 401
    assert r.json()["detail"] == "用户名或密码错误"


def test_not_logged_in(client):
    assert client().get("/api/me").status_code == 401
    assert client().get("/api/requests").status_code == 401


def test_logout(client):
    c = client("chenjie")
    assert c.post("/api/logout").status_code == 204
    assert c.get("/api/me").status_code == 401


# 完整流程 --------------------------------------------------------------

def test_leave_flow(client):
    chenjie, zhangwei = client("chenjie"), client("zhangwei")
    rid = new(chenjie, LEAVE)
    assert detail(chenjie, rid)["status"] == "draft"

    r = act(chenjie, rid, "submit")
    assert r.status_code == 200
    assert r.json()["status"] == "pending"
    assert rid in [x["id"] for x in zhangwei.get("/api/requests/todo").json()]

    r = act(zhangwei, rid, "approve", comment="好")
    assert r.json()["status"] == "approved"
    assert rid not in [x["id"] for x in zhangwei.get("/api/requests/todo").json()]
    history = detail(chenjie, rid)["approvals"]
    assert [(a["step"], a["decision"], a["approver_name"]) for a in history] == [(1, "approve", "张伟")]


def test_expense_two_steps(client):
    chenjie, zhangwei, wangfang = client("chenjie"), client("zhangwei"), client("wangfang")
    rid = new(chenjie, EXPENSE)
    act(chenjie, rid, "submit")

    # 第 1 级是经理，财务这时还不能审
    assert act(wangfang, rid, "approve").status_code == 403
    r = act(zhangwei, rid, "approve")
    assert r.json()["status"] == "pending"
    assert r.json()["current_step"] == 2

    # 第 2 级是财务，经理不能再审
    assert act(zhangwei, rid, "approve").status_code == 403
    assert rid in [x["id"] for x in wangfang.get("/api/requests/todo").json()]
    r = act(wangfang, rid, "approve")
    assert r.json()["status"] == "approved"
    assert [a["step"] for a in r.json()["approvals"]] == [1, 2]


def test_reject_then_resubmit(client):
    chenjie, zhangwei = client("chenjie"), client("zhangwei")
    rid = new(chenjie, LEAVE)
    act(chenjie, rid, "submit")

    assert fields(act(zhangwei, rid, "reject", comment="  ")) == {"comment"}
    r = act(zhangwei, rid, "reject", comment="时间不合适")
    assert r.json()["status"] == "rejected"

    assert act(chenjie, rid, "reopen").json()["status"] == "draft"
    body = {"title": "回家（改期）", "leave": {**LEAVE["leave"], "start_date": "2026-11-09",
                                             "end_date": "2026-11-10"}}
    version = detail(chenjie, rid)["version"]
    assert chenjie.put(f"/api/requests/{rid}", json={**body, "version": version}).status_code == 200
    r = act(chenjie, rid, "submit")
    assert r.json()["round"] == 2
    assert r.json()["current_step"] == 1

    r = act(zhangwei, rid, "approve")
    assert r.json()["status"] == "approved"
    # 第一轮的驳回记录还在
    assert [(a["round"], a["decision"]) for a in r.json()["approvals"]] == [(1, "reject"), (2, "approve")]


def test_withdraw(client):
    chenjie, zhangwei = client("chenjie"), client("zhangwei")
    assert act(chenjie, 1, "withdraw").json()["status"] == "withdrawn"
    assert 1 not in [x["id"] for x in zhangwei.get("/api/requests/todo").json()]
    assert act(zhangwei, 1, "approve").status_code == 409


def test_edit_and_delete_draft(client):
    chenjie = client("chenjie")
    d = detail(chenjie, 6)
    assert set(d["actions"]) == {"edit", "delete", "submit"}
    body = {"title": "显示器支架", "version": d["version"],
            "expense": {"category": "office", "amount": "99", "reason": "工位太矮"}}
    r = chenjie.put("/api/requests/6", json=body)
    assert r.status_code == 200
    assert float(r.json()["expense"]["amount"]) == 99

    version = r.json()["version"]
    assert chenjie.delete(f"/api/requests/6?version={version}").status_code == 204
    assert chenjie.get("/api/requests/6").status_code == 404


def test_list_mine_filter(client):
    chenjie = client("chenjie")
    assert {x["id"] for x in chenjie.get("/api/requests").json()} == {1, 2, 6}
    assert [x["id"] for x in chenjie.get("/api/requests?status=draft").json()] == [6]
    assert fields(chenjie.get("/api/requests?status=nothing")) == {"status"}


# 输入错误 422 ----------------------------------------------------------

def test_leave_validation(client):
    c = client("chenjie")
    bad = {**LEAVE, "client_key": str(uuid.uuid4()),
           "leave": {**LEAVE["leave"], "start_date": "2026-11-03", "end_date": "2026-11-02"}}
    assert fields(c.post("/api/requests", json=bad)) == {"leave.end_date"}

    bad["leave"] = {**LEAVE["leave"], "days": "3"}  # 两天的跨度请三天
    assert fields(c.post("/api/requests", json=bad)) == {"leave.days"}

    bad["leave"] = {**LEAVE["leave"], "days": "1.3"}
    assert "leave.days" in fields(c.post("/api/requests", json=bad))


def test_expense_validation(client):
    c = client("chenjie")
    for amount in ["0", "-1", "1.234", "100000.01", "abc"]:
        bad = {**EXPENSE, "client_key": str(uuid.uuid4()),
               "expense": {**EXPENSE["expense"], "amount": amount}}
        assert fields(c.post("/api/requests", json=bad)) == {"expense.amount"}, amount


def test_body_must_match_type(client):
    c = client("chenjie")
    no_detail = {"type": "leave", "title": "x", "client_key": str(uuid.uuid4())}
    assert fields(c.post("/api/requests", json=no_detail)) == {"leave"}
    both = {**LEAVE, "expense": EXPENSE["expense"], "client_key": str(uuid.uuid4())}
    assert fields(c.post("/api/requests", json=both)) == {"expense"}


def test_blank_title_and_unknown_field(client):
    c = client("chenjie")
    body = {**LEAVE, "title": "   ", "client_key": str(uuid.uuid4())}
    assert fields(c.post("/api/requests", json=body)) == {"title"}
    body = {**LEAVE, "client_key": str(uuid.uuid4()), "status": "approved"}
    assert fields(c.post("/api/requests", json=body)) == {"status"}


# 权限 403 / 404 --------------------------------------------------------

def test_draft_only_visible_to_applicant(client):
    for name in ["zhangwei", "wangfang", "admin", "liuyang"]:
        assert client(name).get("/api/requests/6").status_code == 403, name


def test_other_department_manager_cannot_view(client):
    # 2 号是技术部的报销，市场部经理李娜看不到
    lina = client("lina")
    r = lina.get("/api/requests/2")
    assert r.status_code == 403
    assert "title" not in r.text
    assert act(client("zhangwei"), 2, "approve").status_code == 403  # 第 2 级不归经理


def test_finance_sees_expense_not_leave(client):
    wangfang = client("wangfang")
    assert wangfang.get("/api/requests/2").status_code == 200
    assert wangfang.get("/api/requests/1").status_code == 403


def test_applicant_actions_only_by_applicant(client):
    zhangwei = client("zhangwei")
    version = detail(zhangwei, 1)["version"]
    r = zhangwei.post("/api/requests/1/withdraw", json={"version": version})
    assert r.status_code == 403


def test_cannot_approve_own_request(client):
    # 5 号是经理张伟自己的请假，张伟不能审，由管理员审
    zhangwei, admin = client("zhangwei"), client("admin")
    assert 5 not in [x["id"] for x in zhangwei.get("/api/requests/todo").json()]
    r = act(zhangwei, 5, "approve")
    assert r.status_code == 403
    assert r.json()["detail"] == "不能审批自己的申请"
    assert 5 in [x["id"] for x in admin.get("/api/requests/todo").json()]
    assert act(admin, 5, "approve").json()["status"] == "approved"


def test_admin_without_department_cannot_apply(client):
    r = client("admin").post("/api/requests", json={**LEAVE, "client_key": str(uuid.uuid4())})
    assert r.status_code == 403


def test_not_found(client):
    assert client("chenjie").get("/api/requests/999").status_code == 404


# 状态和重复操作 409 ----------------------------------------------------

def test_wrong_status(client):
    chenjie = client("chenjie")
    assert act(client("liuyang"), 4, "withdraw").status_code == 409  # 已通过的不能撤回
    assert act(client("zhangwei"), 1, "reopen").status_code == 409  # 审批中不能重新编辑
    version = detail(chenjie, 1)["version"]
    body = {"title": "改", "version": version, "leave": LEAVE["leave"]}
    assert chenjie.put("/api/requests/1", json=body).status_code == 409  # 审批中不能修改


def test_duplicate_create_returns_same_request(client):
    c = client("chenjie")
    body = {**LEAVE, "client_key": str(uuid.uuid4())}
    first = c.post("/api/requests", json=body).json()["id"]
    second = c.post("/api/requests", json=body).json()["id"]
    assert first == second
    assert len(c.get("/api/requests?status=draft").json()) == 2  # 原来的 6 号加这一张


def test_concurrent_edit(client):
    # 同一张草稿在两个标签页里打开，先保存的成功，后保存的拿着旧版本号失败
    chenjie = client("chenjie")
    version = detail(chenjie, 6)["version"]
    body = {"title": "支架", "version": version,
            "expense": {"category": "office", "amount": "129", "reason": "工位太矮"}}
    assert chenjie.put("/api/requests/6", json=body).status_code == 200
    r = chenjie.put("/api/requests/6", json={**body, "title": "支架2"})
    assert r.status_code == 409
    assert detail(chenjie, 6)["title"] == "支架"


def test_stale_version(client):
    # 两个人打开了同一张单，张伟先通过了，管理员拿着旧版本号再审
    zhangwei, admin = client("zhangwei"), client("admin")
    version = detail(admin, 1)["version"]
    assert act(zhangwei, 1, "approve").status_code == 200
    r = admin.post("/api/requests/1/approve", json={"version": version, "comment": ""})
    assert r.status_code == 409
    assert len(detail(admin, 1)["approvals"]) == 1


def test_double_click_approve(client):
    # 同一个人拿同一个版本号连发两次
    zhangwei = client("zhangwei")
    version = detail(zhangwei, 1)["version"]
    first = zhangwei.post("/api/requests/1/approve", json={"version": version, "comment": ""})
    second = zhangwei.post("/api/requests/1/approve", json={"version": version, "comment": ""})
    assert first.status_code == 200
    assert second.status_code == 409


def test_html_in_title_is_stored_as_text(client):
    c = client("chenjie")
    rid = new(c, {**LEAVE, "title": "<script>alert(1)</script>"})
    assert detail(c, rid)["title"] == "<script>alert(1)</script>"
