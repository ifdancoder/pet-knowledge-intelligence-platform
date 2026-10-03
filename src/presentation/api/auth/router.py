from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from application.auth.command_handlers import (
    LoginCommandHandler,
    LogoutCommandHandler,
    RefreshCommandHandler,
    RegisterUserCommandHandler,
    VerifyEmailCommandHandler,
)
from application.auth.commands import (
    LoginCommand,
    LogoutCommand,
    RefreshCommand,
    RegisterUserCommand,
    VerifyEmailCommand,
)
from infrastructure.database.auth.repository import (
    SqlAlchemyEmailVerificationTokenRepository,
    SqlAlchemyRefreshTokenRepository,
    SqlAlchemyUserRepository,
)
from infrastructure.database.session import get_db
from infrastructure.email.console_sender import ConsoleEmailSender
from presentation.api.auth.schemas import (
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    RegisterRequest,
    RegisterResponse,
    TokenPairResponse,
    VerifyEmailRequest,
)

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


def get_register_handler(session: AsyncSession = Depends(get_db)) -> RegisterUserCommandHandler:
    return RegisterUserCommandHandler(
        SqlAlchemyUserRepository(session),
        SqlAlchemyEmailVerificationTokenRepository(session),
        ConsoleEmailSender(),
    )


def get_verify_email_handler(session: AsyncSession = Depends(get_db)) -> VerifyEmailCommandHandler:
    return VerifyEmailCommandHandler(
        SqlAlchemyUserRepository(session), SqlAlchemyEmailVerificationTokenRepository(session)
    )


def get_login_handler(session: AsyncSession = Depends(get_db)) -> LoginCommandHandler:
    return LoginCommandHandler(SqlAlchemyUserRepository(session), SqlAlchemyRefreshTokenRepository(session))


def get_refresh_handler(session: AsyncSession = Depends(get_db)) -> RefreshCommandHandler:
    return RefreshCommandHandler(SqlAlchemyRefreshTokenRepository(session))


def get_logout_handler(session: AsyncSession = Depends(get_db)) -> LogoutCommandHandler:
    return LogoutCommandHandler(SqlAlchemyRefreshTokenRepository(session))


@router.post("/register", response_model=RegisterResponse, status_code=201)
async def register(
    payload: RegisterRequest, handler: RegisterUserCommandHandler = Depends(get_register_handler)
) -> RegisterResponse:
    user_id = await handler.handle(RegisterUserCommand(email=payload.email, password=payload.password))
    return RegisterResponse(user_id=user_id)


@router.post("/verify-email", status_code=204)
async def verify_email(
    payload: VerifyEmailRequest, handler: VerifyEmailCommandHandler = Depends(get_verify_email_handler)
) -> None:
    await handler.handle(VerifyEmailCommand(token=payload.token))


@router.post("/login", response_model=TokenPairResponse)
async def login(
    payload: LoginRequest, handler: LoginCommandHandler = Depends(get_login_handler)
) -> TokenPairResponse:
    tokens = await handler.handle(LoginCommand(email=payload.email, password=payload.password))
    return TokenPairResponse(access_token=tokens.access_token, refresh_token=tokens.refresh_token)


@router.post("/refresh", response_model=TokenPairResponse)
async def refresh(
    payload: RefreshRequest, handler: RefreshCommandHandler = Depends(get_refresh_handler)
) -> TokenPairResponse:
    tokens = await handler.handle(RefreshCommand(refresh_token=payload.refresh_token))
    return TokenPairResponse(access_token=tokens.access_token, refresh_token=tokens.refresh_token)


@router.post("/logout", status_code=204)
async def logout(
    payload: LogoutRequest, handler: LogoutCommandHandler = Depends(get_logout_handler)
) -> None:
    await handler.handle(LogoutCommand(refresh_token=payload.refresh_token))
