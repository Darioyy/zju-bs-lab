from psycopg import Connection

# 返回给管理页面的列，不带密码哈希
COLUMNS = "u.id, u.username, u.display_name, u.role, u.department_id, u.is_active"


def get_by_username(conn: Connection, username: str) -> dict | None:
    return conn.execute(
        """
        SELECT id, username, display_name, password_hash, role, department_id, is_active
        FROM users
        WHERE username = %s
        """,
        (username,),
    ).fetchone()


def get(conn: Connection, user_id: int) -> dict | None:
    return conn.execute(
        f"SELECT {COLUMNS} FROM users u WHERE u.id = %s", (user_id,)
    ).fetchone()


def list_all(conn: Connection) -> list[dict]:
    """用户列表，带部门名，以及其担任经理的部门名（不是经理为 NULL）。"""
    return conn.execute(
        f"""
        SELECT {COLUMNS}, u.created_at, d.name AS department_name,
               (SELECT string_agg(md.name, '、') FROM departments md
                WHERE md.manager_id = u.id) AS manages
        FROM users u
        LEFT JOIN departments d ON d.id = u.department_id
        ORDER BY u.id
        """
    ).fetchall()


def insert(conn: Connection, username: str, display_name: str, password_hash: str,
           role: str, department_id: int | None) -> int:
    # username 有唯一约束，重复会抛 UniqueViolation
    row = conn.execute(
        """
        INSERT INTO users (username, display_name, password_hash, role, department_id)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING id
        """,
        (username, display_name, password_hash, role, department_id),
    ).fetchone()
    return row["id"]


def update(conn: Connection, user_id: int, display_name: str, role: str,
           department_id: int | None) -> None:
    conn.execute(
        "UPDATE users SET display_name = %s, role = %s, department_id = %s WHERE id = %s",
        (display_name, role, department_id, user_id),
    )


def set_active(conn: Connection, user_id: int, active: bool) -> None:
    conn.execute("UPDATE users SET is_active = %s WHERE id = %s", (active, user_id))


def set_password(conn: Connection, user_id: int, password_hash: str) -> None:
    conn.execute("UPDATE users SET password_hash = %s WHERE id = %s", (password_hash, user_id))
