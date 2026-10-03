import datetime

import pytest

from domain.auth.exceptions import ExpiredAccessTokenError, InvalidAccessTokenError
from infrastructure.security.tokens import (
    create_access_token,
    decode_access_token,
    generate_opaque_token,
    hash_opaque_token,
    hash_password,
    verify_password,
)


def test_hash_and_verify_password_roundtrip() -> None:
    hashed = hash_password("correct-password")
    assert verify_password("correct-password", hashed) is True


def test_verify_password_rejects_wrong_password() -> None:
    hashed = hash_password("correct-password")
    assert verify_password("wrong-password", hashed) is False


def test_access_token_roundtrip() -> None:
    token = create_access_token(user_id="user-123")
    assert decode_access_token(token) == "user-123"


def test_decode_rejects_garbage_token() -> None:
    with pytest.raises(InvalidAccessTokenError):
        decode_access_token("not-a-jwt")


def test_decode_rejects_expired_token(monkeypatch: pytest.MonkeyPatch) -> None:
    import infrastructure.security.tokens as tokens_module

    monkeypatch.setattr(tokens_module, "ACCESS_TOKEN_TTL", datetime.timedelta(seconds=-1))
    token = create_access_token(user_id="user-123")
    with pytest.raises(ExpiredAccessTokenError):
        decode_access_token(token)


def test_opaque_token_hash_is_deterministic_and_long() -> None:
    token = generate_opaque_token()
    assert len(token) > 20
    assert hash_opaque_token(token) == hash_opaque_token(token)
    assert len(hash_opaque_token(token)) == 64
