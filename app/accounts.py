"""管理部门和用户时的规则。

和 workflow.py 一样只有纯函数，不碰数据库和 HTTP，可以单独测试。
user、department 都是字典，键名和数据库列名一致。
"""


def user_errors(admin: dict, role: str, department_id: int | None,
                target: dict | None = None, managed: dict | None = None) -> dict[str, str]:
    """新建或修改用户时，检查角色和部门的搭配。

    admin 是正在操作的管理员；target 是被修改的用户，新建时为 None；
    managed 是 target 当经理的部门，没有为 None。
    返回 {字段: 原因}，没有问题返回空字典。
    """
    errors = {}
    if role != "admin" and department_id is None:
        errors["department_id"] = "普通员工和财务必须属于一个部门"
    if target is not None and target["id"] == admin["id"] and role != "admin":
        # 防止把自己降级后系统里没有管理员可用
        errors["role"] = "不能取消自己的管理员身份"
    if managed is not None and department_id != managed["id"]:
        # 经理调走后原部门的第 1 级就没人审了，所以要先换经理
        errors["department_id"] = (
            f"{target['display_name']}是{managed['name']}的经理，要先给{managed['name']}换经理"
        )
    return errors


def deactivate_error(admin: dict, target: dict, managed: dict | None) -> str | None:
    """停用 target 前的检查，不能停用时返回原因。"""
    if target["id"] == admin["id"]:
        return "不能停用自己"
    if managed is not None:
        return f"{target['display_name']}是{managed['name']}的经理，要先给{managed['name']}换经理"
    return None


def manager_error(department: dict, candidate: dict | None) -> str | None:
    """candidate 能不能当 department 的经理，不能时返回原因。"""
    if candidate is None:
        return "没有这个用户"
    if not candidate["is_active"]:
        return f"{candidate['display_name']}已停用"
    if candidate["department_id"] != department["id"]:
        return f"{candidate['display_name']}不是{department['name']}的人，要先调到{department['name']}"
    return None
