"""密码哈希和登录 token。只用标准库。"""

import base64
import hashlib
import hmac
import secrets

ALGORITHM = "pbkdf2_sha256"
ITERATIONS = 260_000


def hash_password(password: str) -> str:
    """返回 pbkdf2_sha256$迭代次数$盐$哈希，盐每次随机。"""
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, ITERATIONS)
    return "$".join([
        ALGORITHM,
        str(ITERATIONS),
        base64.b64encode(salt).decode(),
        base64.b64encode(digest).decode(),
    ])


def verify_password(password: str, stored: str) -> bool:
    try:
        algorithm, iterations, salt, digest = stored.split("$")
    except ValueError:
        return False
    if algorithm != ALGORITHM:
        return False
    actual = hashlib.pbkdf2_hmac(
        "sha256", password.encode(), base64.b64decode(salt), int(iterations)
    )
    # 逐字节比较到最后，耗时不随“前几个字节对不对”变化
    return hmac.compare_digest(actual, base64.b64decode(digest))


def new_token() -> str:
    return secrets.token_urlsafe(32)


def token_hash(token: str) -> str:
    """数据库里只存 token 的 sha256，64 位十六进制。"""
    return hashlib.sha256(token.encode()).hexdigest()
