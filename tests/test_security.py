from app.security import hash_password, token_hash, verify_password


def test_password_roundtrip():
    stored = hash_password("123456")
    assert verify_password("123456", stored)
    assert not verify_password("1234567", stored)


def test_same_password_different_hash():
    # 盐是随机的
    assert hash_password("123456") != hash_password("123456")


def test_seed_hash_matches():
    # db/seed.sql 里 admin 的哈希，密码 123456
    stored = "pbkdf2_sha256$260000$7NkVpZOjhpLIHpKZ7taSTw==$OPCAtOd/V4BOlZtx6iaAhgHRc1ftTPV+LM6oGklF1f4="
    assert verify_password("123456", stored)


def test_malformed_hash():
    assert not verify_password("123456", "not-a-hash")
    assert not verify_password("123456", "md5$1$abc$def")


def test_token_hash_is_64_hex():
    h = token_hash("abc")
    assert len(h) == 64
    int(h, 16)
