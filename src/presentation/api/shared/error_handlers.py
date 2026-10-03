from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from domain.auth.exceptions import (
    AccountNotActiveError,
    EmailAlreadyRegisteredError,
    ExpiredAccessTokenError,
    InvalidAccessTokenError,
    InvalidCredentialsError,
    InvalidOrExpiredTokenError,
    RefreshTokenReuseError,
)
from domain.shared.exceptions import DomainError

# Extended by Task 16 with workspace exceptions.
EXCEPTION_STATUS: dict[type[DomainError], tuple[str, int]] = {
    EmailAlreadyRegisteredError: ("email_already_registered", 409),
    InvalidCredentialsError: ("invalid_credentials", 401),
    AccountNotActiveError: ("account_not_active", 403),
    InvalidOrExpiredTokenError: ("invalid_or_expired_token", 400),
    RefreshTokenReuseError: ("refresh_token_reuse_detected", 401),
    InvalidAccessTokenError: ("invalid_access_token", 401),
    ExpiredAccessTokenError: ("access_token_expired", 401),
}

_DEFAULT_STATUS = 400


def register_domain_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(DomainError)
    async def handle_domain_error(request: Request, exc: DomainError) -> JSONResponse:
        code, status_code = EXCEPTION_STATUS.get(
            type(exc), (type(exc).__name__, _DEFAULT_STATUS)
        )
        return JSONResponse(
            status_code=status_code, content={"error": {"code": code, "message": exc.message}}
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(
            status_code=500,
            content={"error": {"code": "internal_error", "message": "Internal server error"}},
        )
