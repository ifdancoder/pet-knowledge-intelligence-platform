import logging
from typing import Protocol

logger = logging.getLogger(__name__)


class EmailSender(Protocol):
    async def send_verification_email(self, to: str, token: str) -> None: ...


class ConsoleEmailSender:
    async def send_verification_email(self, to: str, token: str) -> None:
        logger.info("Verification email for %s: token=%s", to, token)
