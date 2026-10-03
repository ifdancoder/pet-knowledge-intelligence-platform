from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from application.auth.services import AuthService
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


def get_auth_service(session: AsyncSession = Depends(get_db)) -> AuthService:
    return AuthService(
        users=SqlAlchemyUserRepository(session),
        verification_tokens=SqlAlchemyEmailVerificationTokenRepository(session),
        refresh_tokens=SqlAlchemyRefreshTokenRepository(session),
        email_sender=ConsoleEmailSender(),
    )


@router.post("/register", response_model=RegisterResponse, status_code=201)
async def register(
    payload: RegisterRequest, service: AuthService = Depends(get_auth_service)
) -> RegisterResponse:
    user_id = await service.register(email=payload.email, password=payload.password)
    return RegisterResponse(user_id=user_id)


@router.post("/verify-email", status_code=204)
async def verify_email(
    payload: VerifyEmailRequest, service: AuthService = Depends(get_auth_service)
) -> None:
    await service.verify_email(token=payload.token)


@router.post("/login", response_model=TokenPairResponse)
async def login(
    payload: LoginRequest, service: AuthService = Depends(get_auth_service)
) -> TokenPairResponse:
    access_token, refresh_token = await service.login(email=payload.email, password=payload.password)
    return TokenPairResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh", response_model=TokenPairResponse)
async def refresh(
    payload: RefreshRequest, service: AuthService = Depends(get_auth_service)
) -> TokenPairResponse:
    access_token, refresh_token = await service.refresh(refresh_token=payload.refresh_token)
    return TokenPairResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/logout", status_code=204)
async def logout(payload: LogoutRequest, service: AuthService = Depends(get_auth_service)) -> None:
    await service.logout(refresh_token=payload.refresh_token)
