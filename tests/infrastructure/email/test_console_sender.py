import logging

from infrastructure.email.console_sender import ConsoleEmailSender


async def test_console_email_sender_logs_the_token(caplog: logging.LogCaptureFixture) -> None:
    sender = ConsoleEmailSender()
    with caplog.at_level(logging.INFO):
        await sender.send_verification_email(to="a@example.com", token="abc123")
    assert "a@example.com" in caplog.text
    assert "abc123" in caplog.text
