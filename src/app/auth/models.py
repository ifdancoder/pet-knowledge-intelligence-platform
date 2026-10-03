from infrastructure.database.auth.models import (
    EmailVerificationTokenModel,
    RefreshTokenModel,
    UserModel,
)

EmailVerificationToken = EmailVerificationTokenModel
RefreshToken = RefreshTokenModel
User = UserModel

__all__ = ["EmailVerificationToken", "RefreshToken", "User"]
