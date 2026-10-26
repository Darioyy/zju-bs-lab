"""接口测试和数据库约束测试用的数据库与客户端。

连一个单独的测试库（默认 approval_test，不存在就自动建），不碰开发用的 approval 库：
整个测试开始时建一次表，每个测试开始前清空所有表、重新导入演示数据。
连不上数据库时，这个目录下的测试全部跳过，tests/ 下的纯逻辑测试照常运行。

换数据库地址：设环境变量 TEST_DATABASE_URL，库名必须以 _test 结尾。
"""

import os
from pathlib import Path

import psycopg
import pytest
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict, make_conninfo
from psycopg.rows import dict_row

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = (ROOT / "db" / "schema.sql").read_text(encoding="utf-8")
SEED = (ROOT / "db" / "seed.sql").read_text(encoding="utf-8")

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/approval_test"
)

PASSWORD = "123456"  # 演示账号的密码


def _create_database_if_missing(url: str) -> None:
    info = conninfo_to_dict(url)
    name = info["dbname"]
    info["dbname"] = "postgres"
    with psycopg.connect(make_conninfo(**info), autocommit=True, connect_timeout=3) as conn:
        exists = conn.execute("SELECT 1 FROM pg_database WHERE datname = %s", (name,)).fetchone()
        if not exists:
            conn.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))


@pytest.fixture(scope="session")
def database() -> str:
    """建好表的测试库地址。"""
    if not conninfo_to_dict(TEST_DATABASE_URL).get("dbname", "").endswith("_test"):
        pytest.exit("TEST_DATABASE_URL 的库名必须以 _test 结尾，免得清掉开发数据", returncode=2)
    try:
        _create_database_if_missing(TEST_DATABASE_URL)
    except psycopg.OperationalError as e:
        pytest.skip(f"连不上测试数据库，跳过接口测试：{e}")
    with psycopg.connect(TEST_DATABASE_URL, autocommit=True) as conn:
        conn.execute(SCHEMA)
    return TEST_DATABASE_URL


@pytest.fixture
def db(database):
    """每个测试一份干净的演示数据，返回一个 autocommit 连接，查询结果是字典。

    清空用 TRUNCATE 而不是重新建表：表结构不变，后端连接池里缓存的查询计划还能用。
    """
    with psycopg.connect(database, autocommit=True, row_factory=dict_row) as conn:
        conn.execute("""
            TRUNCATE approvals, expense_details, leave_details, requests, sessions,
                     users, departments RESTART IDENTITY CASCADE
        """)
        conn.execute(SEED)
        yield conn


@pytest.fixture(scope="session")
def app(database):
    """后端应用，连接池连的是测试库。整个测试过程只打开一次连接池。"""
    # app.config 在第一次导入时读环境变量，所以要先设好再导入
    os.environ["DATABASE_URL"] = database
    from fastapi.testclient import TestClient

    from app import config
    from app.main import app

    if config.DATABASE_URL != database:
        pytest.exit("app.config 在设置测试库地址之前就被导入了，停止测试以免写到开发库", returncode=2)
    with TestClient(app):  # 进入时执行 lifespan，打开连接池
        yield app


@pytest.fixture
def client(app, db):
    """返回一个函数：client("chenjie") 得到一个已登录的客户端，client() 得到未登录的。

    每个客户端有自己的 cookie，相当于不同的浏览器。
    """
    from fastapi.testclient import TestClient

    def make(username: str | None = None):
        c = TestClient(app)
        if username is not None:
            r = c.post("/api/login", json={"username": username, "password": PASSWORD})
            assert r.status_code == 200, r.text
        return c

    return make
