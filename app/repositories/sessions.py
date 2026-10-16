from psycopg import Connection


def create(conn: Connection, token_hash: str, user_id: int, hours: int) -> None:
    conn.execute(
        """
        INSERT INTO sessions (token_hash, user_id, expires_at)
        VALUES (%s, %s, now() + make_interval(hours => %s))
        """,
        (token_hash, user_id, hours),
    )


def get_user(conn: Connection, token_hash: str) -> dict | None:
    """token 有效（没过期、账号没停用）就返回对应用户。"""
    return conn.execute(
        """
        SELECT u.id, u.username, u.display_name, u.role, u.department_id
        FROM sessions s
        JOIN users u ON u.id = s.user_id
        WHERE s.token_hash = %s AND s.expires_at > now() AND u.is_active
        """,
        (token_hash,),
    ).fetchone()


def delete(conn: Connection, token_hash: str) -> None:
    conn.execute("DELETE FROM sessions WHERE token_hash = %s", (token_hash,))


def delete_expired(conn: Connection, user_id: int) -> None:
    conn.execute(
        "DELETE FROM sessions WHERE user_id = %s AND expires_at <= now()", (user_id,)
    )
