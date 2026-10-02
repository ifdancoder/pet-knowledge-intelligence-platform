import pytest
from pydantic import ValidationError

from app.auth.schemas import LoginRequest, RegisterRequest


def test_register_request_rejects_short_password() -> None:
    with pytest.raises(ValidationError):
        RegisterRequest(email="a@example.com", password="short")


def test_register_request_rejects_invalid_email() -> None:
    with pytest.raises(ValidationError):
        RegisterRequest(email="not-an-email", password="longenoughpassword")


def test_register_request_accepts_valid_input() -> None:
    request = RegisterRequest(email="a@example.com", password="longenoughpassword")
    assert request.email == "a@example.com"


def test_login_request_accepts_valid_input() -> None:
    request = LoginRequest(email="a@example.com", password="anything")
    assert request.password == "anything"
