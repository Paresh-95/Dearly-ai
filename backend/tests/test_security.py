from uuid import uuid4

from app.core.security import create_token, decode_token, hash_password, verify_password


def test_password_hash_roundtrip():
    h = hash_password("s3cret-passphrase")
    assert h != "s3cret-passphrase"
    assert verify_password("s3cret-passphrase", h)
    assert not verify_password("wrong", h)
    assert not verify_password("anything", "not-a-hash")


def test_token_types_are_not_interchangeable():
    uid = uuid4()
    access, refresh = create_token(uid, "access"), create_token(uid, "refresh")
    assert decode_token(access, "access") == uid
    assert decode_token(refresh, "refresh") == uid
    assert decode_token(access, "refresh") is None
    assert decode_token(refresh, "access") is None
    assert decode_token("garbage", "access") is None
