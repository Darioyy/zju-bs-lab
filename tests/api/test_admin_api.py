"""管理部门和用户的接口测试。演示数据见 db/seed.sql：

  部门 1 技术部（经理张伟） 2 市场部（经理李娜） 3 财务部（经理王芳）
  用户 1 admin  2 zhangwei  3 lina  4 wangfang（财务）  5 chenjie  6 liuyang
"""

NEW_USER = {"username": "zhaolei", "display_name": "赵磊", "role": "staff",
            "department_id": 1, "password": "abc123"}


def fields(r):
    assert r.status_code == 422, r.text
    return {".".join(e["loc"][1:]) for e in r.json()["detail"]}


def user(admin, user_id):
    return next(u for u in admin.get("/api/admin/users").json() if u["id"] == user_id)


def dept(admin, dept_id):
    return next(d for d in admin.get("/api/admin/departments").json() if d["id"] == dept_id)


def edit_user(admin, user_id, **changes):
    u = user(admin, user_id)
    body = {"display_name": u["display_name"], "role": u["role"], "department_id": u["department_id"]}
    return admin.put(f"/api/admin/users/{user_id}", json={**body, **changes})


def login(client, username, password):
    """用指定密码登录（client 夹具只会用演示密码）。"""
    c = client()
    r = c.post("/api/login", json={"username": username, "password": password})
    assert r.status_code == 200, r.text
    return c


def todo_ids(c):
    return [x["id"] for x in c.get("/api/requests/todo").json()]


# 只有管理员能用 --------------------------------------------------------

def test_only_admin(client):
    for name in ["chenjie", "zhangwei", "wangfang"]:
        c = client(name)
        assert c.get("/api/admin/users").status_code == 403, name
        assert c.post("/api/admin/departments", json={"name": "x"}).status_code == 403, name
    assert client().get("/api/admin/users").status_code == 401


def test_lists(client):
    admin = client("admin")
    users = admin.get("/api/admin/users").json()
    assert len(users) == 6
    assert all("password_hash" not in u for u in users)
    assert user(admin, 2)["manages"] == "技术部"
    assert user(admin, 5)["manages"] is None
    tech = dept(admin, 1)
    assert tech["manager_name"] == "张伟"
    assert tech["member_count"] == 2


# 部门 ------------------------------------------------------------------

def test_create_and_rename_department(client):
    admin = client("admin")
    r = admin.post("/api/admin/departments", json={"name": "  人事部 "})
    assert r.status_code == 201
    new_id = r.json()["id"]
    assert dept(admin, new_id)["name"] == "人事部"

    assert fields(admin.post("/api/admin/departments", json={"name": "人事部"})) == {"name"}
    assert fields(admin.post("/api/admin/departments", json={"name": ""})) == {"name"}

    r = admin.put(f"/api/admin/departments/{new_id}", json={"name": "人力资源部", "manager_id": None})
    assert r.status_code == 204
    assert dept(admin, new_id)["name"] == "人力资源部"
    # 改成别的部门的名字
    r = admin.put(f"/api/admin/departments/{new_id}", json={"name": "技术部", "manager_id": None})
    assert fields(r) == {"name"}
    assert admin.put("/api/admin/departments/999", json={"name": "x"}).status_code == 404


def test_manager_must_be_active_member(client):
    admin = client("admin")
    # 陈杰是技术部的，不能当市场部经理
    r = admin.put("/api/admin/departments/2", json={"name": "市场部", "manager_id": 5})
    assert fields(r) == {"manager_id"}
    r = admin.put("/api/admin/departments/2", json={"name": "市场部", "manager_id": 999})
    assert fields(r) == {"manager_id"}
    assert dept(admin, 2)["manager_id"] == 3


def test_change_manager_moves_pending_requests(client):
    # 1 号单停在技术部第 1 级。把技术部经理换成新来的赵磊，单子就转给赵磊审
    admin = client("admin")
    new_id = admin.post("/api/admin/users", json=NEW_USER).json()["id"]
    r = admin.put("/api/admin/departments/1", json={"name": "技术部", "manager_id": new_id})
    assert r.status_code == 204

    assert 1 in todo_ids(login(client, "zhaolei", "abc123"))
    assert 1 not in todo_ids(client("zhangwei"))


def test_department_without_manager(client):
    # 技术部不设经理时，第 1 级只有管理员能审
    admin = client("admin")
    r = admin.put("/api/admin/departments/1", json={"name": "技术部", "manager_id": None})
    assert r.status_code == 204
    assert 1 not in todo_ids(client("zhangwei"))
    assert 1 in todo_ids(admin)


# 用户 ------------------------------------------------------------------

def test_create_user_andlogin(client):
    admin = client("admin")
    r = admin.post("/api/admin/users", json=NEW_USER)
    assert r.status_code == 201
    c = login(client, "zhaolei", "abc123")
    me = c.get("/api/me").json()
    assert me["display_name"] == "赵磊"
    assert me["department_id"] == 1


def test_password_spaces_are_kept(client):
    admin = client("admin")
    admin.post("/api/admin/users", json={**NEW_USER, "password": " abc123 "})
    login(client, "zhaolei", " abc123 ")
    r = client().post("/api/login", json={"username": "zhaolei", "password": "abc123"})
    assert r.status_code == 401


def test_create_user_validation(client):
    admin = client("admin")
    assert fields(admin.post("/api/admin/users", json={**NEW_USER, "username": "chenjie"})) == {"username"}
    for bad in ["ab", "Zhao", "zhao lei", "赵磊", "a" * 33]:
        assert fields(admin.post("/api/admin/users", json={**NEW_USER, "username": bad})) == {"username"}, bad
    assert fields(admin.post("/api/admin/users", json={**NEW_USER, "password": "12345"})) == {"password"}
    assert fields(admin.post("/api/admin/users", json={**NEW_USER, "display_name": "  "})) == {"display_name"}
    assert fields(admin.post("/api/admin/users", json={**NEW_USER, "role": "boss"})) == {"role"}
    # 普通员工和财务必须有部门，部门要存在
    assert fields(admin.post("/api/admin/users", json={**NEW_USER, "department_id": None})) == {"department_id"}
    assert fields(admin.post("/api/admin/users", json={**NEW_USER, "department_id": 999})) == {"department_id"}
    # 管理员可以没有部门
    r = admin.post("/api/admin/users", json={**NEW_USER, "role": "admin", "department_id": None})
    assert r.status_code == 201


def test_edit_user(client):
    admin = client("admin")
    assert edit_user(admin, 5, role="finance", department_id=3, display_name="陈杰杰").status_code == 204
    u = user(admin, 5)
    assert (u["role"], u["department_id"], u["display_name"]) == ("finance", 3, "陈杰杰")
    # 改完马上生效：陈杰现在是财务，能看别人的报销单
    assert client("chenjie").get("/api/requests/3").status_code == 200


def test_manager_cannot_leave_department(client):
    admin = client("admin")
    assert fields(edit_user(admin, 2, department_id=2)) == {"department_id"}
    assert fields(edit_user(admin, 2, role="admin", department_id=None)) == {"department_id"}
    assert user(admin, 2)["department_id"] == 1
    # 角色可以改，部门不变就行
    assert edit_user(admin, 2, role="finance").status_code == 204


def test_admin_cannot_demote_self(client):
    admin = client("admin")
    assert fields(edit_user(admin, 1, role="staff", department_id=1)) == {"role"}
    assert user(admin, 1)["role"] == "admin"


def test_deactivate_and_activate(client):
    admin, chenjie = client("admin"), client("chenjie")
    assert admin.post("/api/admin/users/5/deactivate").status_code == 204
    assert user(admin, 5)["is_active"] is False
    # 已登录的立刻失效，也登不进来
    assert chenjie.get("/api/me").status_code == 401
    r = client().post("/api/login", json={"username": "chenjie", "password": "123456"})
    assert r.status_code == 401
    # 以前提交的单子还在，名字照常显示
    assert client("zhangwei").get("/api/requests/1").json()["applicant_name"] == "陈杰"

    assert admin.post("/api/admin/users/5/activate").status_code == 204
    client("chenjie")


def test_cannot_deactivate_self_or_manager(client):
    admin = client("admin")
    assert admin.post("/api/admin/users/1/deactivate").status_code == 409
    r = admin.post("/api/admin/users/2/deactivate")
    assert r.status_code == 409
    assert "技术部" in r.json()["detail"]
    assert admin.post("/api/admin/users/999/deactivate").status_code == 404


def test_deactivated_user_cannot_be_manager(client):
    admin = client("admin")
    admin.post("/api/admin/users/5/deactivate")
    r = admin.put("/api/admin/departments/1", json={"name": "技术部", "manager_id": 5})
    assert fields(r) == {"manager_id"}


def test_reset_password(client):
    admin, chenjie = client("admin"), client("chenjie")
    assert fields(admin.post("/api/admin/users/5/password", json={"password": "123"})) == {"password"}
    assert admin.post("/api/admin/users/5/password", json={"password": "newpass"}).status_code == 204
    assert chenjie.get("/api/me").status_code == 401
    r = client().post("/api/login", json={"username": "chenjie", "password": "123456"})
    assert r.status_code == 401
    login(client, "chenjie", "newpass")
