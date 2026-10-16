"""数据库连接池。

连接设成 autocommit：单条语句执行完就生效；要多条语句一起成功或一起失败时，
在 service 里显式写 with conn.transaction():，事务从哪开始到哪结束一眼能看到。
"""

from psycopg import Connection
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from . import config

pool = ConnectionPool(
    config.DATABASE_URL,
    open=False,  # 在 main.py 的 lifespan 里打开
    kwargs={"autocommit": True, "row_factory": dict_row},  # 查询结果是字典
)


def get_conn():
    """FastAPI 依赖：每个请求从池里借一个连接，用完还回去。"""
    with pool.connection() as conn:
        yield conn


__all__ = ["Connection", "pool", "get_conn"]
