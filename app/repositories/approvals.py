from psycopg import Connection


def insert(conn: Connection, request_id: int, round_: int, step: int,
           approver_id: int, decision: str, comment: str) -> None:
    # (request_id, round, step) 有唯一约束，同一级重复插入会抛 UniqueViolation
    conn.execute(
        """
        INSERT INTO approvals (request_id, round, step, approver_id, decision, comment)
        VALUES (%s, %s, %s, %s, %s, %s)
        """,
        (request_id, round_, step, approver_id, decision, comment),
    )


def list_by_request(conn: Connection, request_id: int) -> list[dict]:
    return conn.execute(
        """
        SELECT a.round, a.step, a.decision, a.comment, a.created_at,
               u.display_name AS approver_name, u.role AS approver_role
        FROM approvals a
        JOIN users u ON u.id = a.approver_id
        WHERE a.request_id = %s
        ORDER BY a.round, a.step
        """,
        (request_id,),
    ).fetchall()
