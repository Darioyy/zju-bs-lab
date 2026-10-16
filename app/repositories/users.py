from psycopg import Connection


def get_by_username(conn: Connection, username: str) -> dict | None:
    return conn.execute(
        """
        SELECT id, username, display_name, password_hash, role, department_id, is_active
        FROM users
        WHERE username = %s
        """,
        (username,),
    ).fetchone()
