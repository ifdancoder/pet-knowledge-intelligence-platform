from fastapi import Header

from domain.auth.exceptions import InvalidAccessTokenError
from infrastructure.security.tokens import decode_access_token


async def get_current_user_id(authorization: str = Header(...)) -> str:
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise InvalidAccessTokenError("missing bearer token")
    return decode_access_token(token)
