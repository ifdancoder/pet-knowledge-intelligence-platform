from fastapi import APIRouter, Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.email_sender import ConsoleEmailSender
from app.auth.repository import (
    SqlAlchemyEmailVerificationTokenRepository,
    SqlAlchemyRefreshTokenRepository,
    SqlAlchemyUserRepository,
)
from app.auth.schemas import (
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    RegisterRequest,
    RegisterResponse,
    TokenPairResponse,
    VerifyEmailRequest,
)
from app.auth.security import InvalidAccessTokenError, decode_access_token
from app.auth.service import AuthService
from app.shared.db import get_db

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


async def get_current_user_id(authorization: str = Header(...)) -> str:
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise InvalidAccessTokenError("missing bearer token")
    return decode_access_token(token)
