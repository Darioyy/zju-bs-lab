from uuid import UUID

from psycopg import Connection, sql

# 单据加上申请人姓名、部门名和部门经理，权限判断要用 manager_id
SELECT_REQUEST = """
    SELECT r.*, u.display_name AS applicant_name,
           d.name AS department_name, d.manager_id
    FROM requests r
    JOIN users u ON u.id = r.applicant_id
    JOIN departments d ON d.id = r.department_id
"""

# update_fields 只允许改这些列，防止调用方传进别的列名拼进 SQL
UPDATABLE = {"title", "status", "round", "total_steps", "current_step",
             "submitted_at", "finished_at"}


def get(conn: Connection, request_id: int) -> dict | None:
    return conn.execute(SELECT_REQUEST + "WHERE r.id = %s", (request_id,)).fetchone()


def list_by_applicant(conn: Connection, applicant_id: int, status: str | None) -> list[dict]:
    query = SELECT_REQUEST + "WHERE r.applicant_id = %s"
    params: list = [applicant_id]
    if status:
        query += " AND r.status = %s"
        params.append(status)
    query += " ORDER BY r.created_at DESC"
    return conn.execute(query, params).fetchall()


def list_todo(conn: Connection, user: dict) -> list[dict]:
    """待 user 审批的单子。条件和 workflow.can_approve 一致，改一处要同时改另一处。"""
    return conn.execute(
        SELECT_REQUEST + """
        WHERE r.status = 'pending'
          AND r.applicant_id <> %(uid)s
          AND (%(is_admin)s
               OR (r.current_step = 1 AND d.manager_id = %(uid)s)
               OR (r.current_step = 2 AND %(is_finance)s))
        ORDER BY r.submitted_at
        """,
        {"uid": user["id"],
         "is_admin": user["role"] == "admin",
         "is_finance": user["role"] == "finance"},
    ).fetchall()


def insert(conn: Connection, applicant_id: int, department_id: int,
           type_: str, title: str, client_key: UUID) -> int | None:
    """新建草稿，返回 id。同一个人的 client_key 已经用过时什么也不做，返回 None。"""
    row = conn.execute(
        """
        INSERT INTO requests (type, title, applicant_id, department_id, client_key)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (applicant_id, client_key) DO NOTHING
        RETURNING id
        """,
        (type_, title, applicant_id, department_id, client_key),
    ).fetchone()
    return row["id"] if row else None


def find_by_client_key(conn: Connection, applicant_id: int, client_key: UUID) -> int:
    row = conn.execute(
        "SELECT id FROM requests WHERE applicant_id = %s AND client_key = %s",
        (applicant_id, client_key),
    ).fetchone()
    return row["id"]


def update_fields(conn: Connection, request_id: int, version: int, changes: dict) -> dict | None:
    """按版本号更新单据，version 自动加 1。

    版本号对不上（单子已经被别人改过）时一行都不会更新，返回 None。
    """
    if not changes or not set(changes) <= UPDATABLE:
        raise ValueError(f"不能更新这些列：{set(changes) - UPDATABLE}")
    assignments = sql.SQL(", ").join(
        sql.SQL("{} = %s").format(sql.Identifier(column)) for column in changes
    )
    query = sql.SQL("""
        UPDATE requests
        SET {}, version = version + 1, updated_at = now()
        WHERE id = %s AND version = %s
        RETURNING id, version
    """).format(assignments)
    return conn.execute(query, [*changes.values(), request_id, version]).fetchone()


def delete_draft(conn: Connection, request_id: int, version: int) -> bool:
    row = conn.execute(
        """
        DELETE FROM requests
        WHERE id = %s AND version = %s AND status = 'draft'
        RETURNING id
        """,
        (request_id, version),
    ).fetchone()
    return row is not None


# 明细表 ----------------------------------------------------------------
# 新建和修改都用 INSERT ... ON CONFLICT DO UPDATE，有就改、没有就插

def save_leave(conn: Connection, request_id: int, leave) -> None:
    conn.execute(
        """
        INSERT INTO leave_details (request_id, kind, start_date, end_date, days, reason)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (request_id) DO UPDATE
        SET kind = EXCLUDED.kind, start_date = EXCLUDED.start_date,
            end_date = EXCLUDED.end_date, days = EXCLUDED.days, reason = EXCLUDED.reason
        """,
        (request_id, leave.kind, leave.start_date, leave.end_date, leave.days, leave.reason),
    )


def save_expense(conn: Connection, request_id: int, expense) -> None:
    conn.execute(
        """
        INSERT INTO expense_details (request_id, category, amount, reason)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (request_id) DO UPDATE
        SET category = EXCLUDED.category, amount = EXCLUDED.amount, reason = EXCLUDED.reason
        """,
        (request_id, expense.category, expense.amount, expense.reason),
    )


def get_leave(conn: Connection, request_id: int) -> dict | None:
    return conn.execute(
        "SELECT kind, start_date, end_date, days, reason FROM leave_details WHERE request_id = %s",
        (request_id,),
    ).fetchone()


def get_expense(conn: Connection, request_id: int) -> dict | None:
    return conn.execute(
        "SELECT category, amount, reason FROM expense_details WHERE request_id = %s",
        (request_id,),
    ).fetchone()
