from __future__ import annotations

import datetime
from dataclasses import dataclass

from shared.ids import generate_id


@dataclass
class User:
    id: str
    email: str
    hashed_password: str
    is_active: bool = False

    @classmethod
    def register(cls, *, email: str, hashed_password: str) -> User:
        return cls(id=generate_id(), email=email, hashed_password=hashed_password, is_active=False)

    def activate(self) -> None:
        self.is_active = True


@dataclass
class EmailVerificationToken:
    id: str
    user_id: str
    token_hash: str
    expires_at: datetime.datetime
    used_at: datetime.datetime | None = None

    @classmethod
    def issue(
        cls, *, user_id: str, token_hash: str, ttl: datetime.timedelta, now: datetime.datetime
    ) -> EmailVerificationToken:
        return cls(id=generate_id(), user_id=user_id, token_hash=token_hash, expires_at=now + ttl)

    def is_valid(self, now: datetime.datetime) -> bool:
        return self.used_at is None and self.expires_at >= now

    def mark_used(self, now: datetime.datetime) -> None:
        self.used_at = now


@dataclass
class RefreshToken:
    id: str
    user_id: str
    token_hash: str
    expires_at: datetime.datetime
    revoked_at: datetime.datetime | None = None
    replaced_by_id: str | None = None

    @classmethod
    def issue(
        cls, *, user_id: str, token_hash: str, ttl: datetime.timedelta, now: datetime.datetime
    ) -> RefreshToken:
        return cls(id=generate_id(), user_id=user_id, token_hash=token_hash, expires_at=now + ttl)

    def is_usable(self, now: datetime.datetime) -> bool:
        return self.revoked_at is None and self.expires_at >= now

    def revoke(self, now: datetime.datetime, replaced_by_id: str | None = None) -> None:
        self.revoked_at = now
        self.replaced_by_id = replaced_by_id
