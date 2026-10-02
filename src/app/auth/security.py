import datetime
import hashlib
import os
import secrets

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from app.shared.exceptions import AppError

_hasher = PasswordHasher()

JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_TTL = datetime.timedelta(minutes=15)


def _jwt_secret() -> str:
    return os.environ["JWT_SECRET"]


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    try:
        return _hasher.verify(hashed, password)
    except VerifyMismatchError:
        return False


class InvalidAccessTokenError(AppError):
    code = "invalid_access_token"
    status_code = 401


class ExpiredAccessTokenError(AppError):
    code = "access_token_expired"
    status_code = 401


def create_access_token(user_id: str) -> str:
    now = datetime.datetime.now(datetime.UTC)
    payload = {"sub": user_id, "iat": now, "exp": now + ACCESS_TOKEN_TTL}
    return jwt.encode(payload, _jwt_secret(), algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> str:
    try:
        payload = jwt.decode(token, _jwt_secret(), algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError as exc:
        raise ExpiredAccessTokenError("access token has expired") from exc
    except jwt.InvalidTokenError as exc:
        raise InvalidAccessTokenError("access token is invalid") from exc
    return str(payload["sub"])


def generate_opaque_token() -> str:
    return secrets.token_urlsafe(32)


def hash_opaque_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()
