"""配置，全部从环境变量读，没设就用本地开发的默认值。"""

import os

DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/approval"
)

# 登录多久后过期
SESSION_HOURS = int(os.environ.get("SESSION_HOURS", "8"))

# 部署到 https 时设成 1，cookie 只走加密连接
COOKIE_SECURE = os.environ.get("COOKIE_SECURE", "0") == "1"
