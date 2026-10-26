from psycopg import Connection


def list_all(conn: Connection) -> list[dict]:
    """部门列表，带经理姓名和在职人数。"""
    return conn.execute(
        """
        SELECT d.id, d.name, d.manager_id, m.display_name AS manager_name,
               (SELECT count(*) FROM users u
                WHERE u.department_id = d.id AND u.is_active) AS member_count
        FROM departments d
        LEFT JOIN users m ON m.id = d.manager_id
        ORDER BY d.id
        """
    ).fetchall()


def get(conn: Connection, department_id: int) -> dict | None:
    return conn.execute(
        "SELECT id, name, manager_id FROM departments WHERE id = %s", (department_id,)
    ).fetchone()


def managed_by(conn: Connection, user_id: int) -> dict | None:
    """user_id 当经理的部门，不是经理返回 None。"""
    return conn.execute(
        "SELECT id, name, manager_id FROM departments WHERE manager_id = %s ORDER BY id LIMIT 1",
        (user_id,),
    ).fetchone()


def insert(conn: Connection, name: str) -> int:
    # name 有唯一约束，重名会抛 UniqueViolation
    row = conn.execute(
        "INSERT INTO departments (name) VALUES (%s) RETURNING id", (name,)
    ).fetchone()
    return row["id"]


def update(conn: Connection, department_id: int, name: str, manager_id: int | None) -> None:
    conn.execute(
        "UPDATE departments SET name = %s, manager_id = %s WHERE id = %s",
        (name, manager_id, department_id),
    )
