import datetime

from domain.auth.entities import EmailVerificationToken, RefreshToken, User

NOW = datetime.datetime.now(datetime.UTC)


def test_user_register_assigns_id_and_is_inactive() -> None:
    user = User.register(email="a@example.com", hashed_password="hash")
    assert len(user.id) == 26
    assert user.email == "a@example.com"
    assert user.is_active is False


def test_user_activate_sets_is_active() -> None:
    user = User.register(email="a@example.com", hashed_password="hash")
    user.activate()
    assert user.is_active is True


def test_email_verification_token_issue_sets_expiry() -> None:
    token = EmailVerificationToken.issue(
        user_id="u1", token_hash="h" * 64, ttl=datetime.timedelta(hours=24), now=NOW
    )
    assert len(token.id) == 26
    assert token.expires_at == NOW + datetime.timedelta(hours=24)
    assert token.used_at is None


def test_email_verification_token_is_valid_rejects_used() -> None:
    token = EmailVerificationToken.issue(
        user_id="u1", token_hash="h" * 64, ttl=datetime.timedelta(hours=24), now=NOW
    )
    token.mark_used(NOW)
    assert token.is_valid(NOW) is False


def test_email_verification_token_is_valid_rejects_expired() -> None:
    token = EmailVerificationToken.issue(
        user_id="u1", token_hash="h" * 64, ttl=datetime.timedelta(hours=-1), now=NOW
    )
    assert token.is_valid(NOW) is False


def test_email_verification_token_is_valid_accepts_fresh() -> None:
    token = EmailVerificationToken.issue(
        user_id="u1", token_hash="h" * 64, ttl=datetime.timedelta(hours=24), now=NOW
    )
    assert token.is_valid(NOW) is True


def test_refresh_token_is_usable_rejects_revoked() -> None:
    token = RefreshToken.issue(
        user_id="u1", token_hash="h" * 64, ttl=datetime.timedelta(days=30), now=NOW
    )
    token.revoke(NOW)
    assert token.is_usable(NOW) is False


def test_refresh_token_is_usable_rejects_expired() -> None:
    token = RefreshToken.issue(
        user_id="u1", token_hash="h" * 64, ttl=datetime.timedelta(hours=-1), now=NOW
    )
    assert token.is_usable(NOW) is False


def test_refresh_token_revoke_records_replacement() -> None:
    token = RefreshToken.issue(
        user_id="u1", token_hash="h" * 64, ttl=datetime.timedelta(days=30), now=NOW
    )
    token.revoke(NOW, replaced_by_id="new-id")
    assert token.revoked_at == NOW
    assert token.replaced_by_id == "new-id"
