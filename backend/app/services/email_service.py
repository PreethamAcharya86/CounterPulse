import abc
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from backend.app.core.config import settings

logger = logging.getLogger(__name__)

class EmailServiceError(Exception):
    """Base exception for email service failures."""
    pass

class EmailConfigurationError(EmailServiceError):
    """Raised when email provider credentials or settings are missing or invalid."""
    pass

class EmailDispatchError(EmailServiceError):
    """Raised when an email dispatch attempt fails with the provider."""
    pass

class EmailProvider(abc.ABC):
    """Abstract base class for email delivery providers."""

    @abc.abstractmethod
    def send_email(self, to_email: str, subject: str, body: str) -> Dict[str, Any]:
        """Send plain text email."""
        pass

    @abc.abstractmethod
    def send_email_with_attachment(
        self,
        to_email: str,
        subject: str,
        body: str,
        attachment_bytes: bytes,
        attachment_filename: str,
    ) -> Dict[str, Any]:
        """Send email with an attachment (e.g., PDF dossier)."""
        pass

class ResendEmailProvider(EmailProvider):
    """
    Real email delivery via Resend API SDK.
    Requires RESEND_API_KEY environment variable.
    """

    def __init__(self, api_key: Optional[str] = None, from_email: Optional[str] = None):
        self.api_key = api_key or settings.RESEND_API_KEY
        self.from_email = from_email or settings.EMAIL_FROM

    def _ensure_configured(self):
        if not self.api_key or self.api_key.strip() == "":
            raise EmailConfigurationError(
                "Resend API key is not configured. Set RESEND_API_KEY in your environment or .env file."
            )

    def send_email(self, to_email: str, subject: str, body: str) -> Dict[str, Any]:
        self._ensure_configured()
        import resend
        resend.api_key = self.api_key

        params = {
            "from": self.from_email,
            "to": [to_email],
            "subject": subject,
            "text": body,
        }

        try:
            resp = resend.Emails.send(params)
            msg_id = resp.get("id") if isinstance(resp, dict) else getattr(resp, "id", str(resp))
            logger.info("Resend email sent successfully to %s, id: %s", to_email, msg_id)
            return {
                "id": str(msg_id),
                "provider": "resend",
                "recipient": to_email,
                "status": "sent",
            }
        except Exception as e:
            logger.error("Resend email dispatch error: %s", str(e))
            raise EmailDispatchError(f"Resend dispatch failed: {str(e)}") from e

    def send_email_with_attachment(
        self,
        to_email: str,
        subject: str,
        body: str,
        attachment_bytes: bytes,
        attachment_filename: str,
    ) -> Dict[str, Any]:
        self._ensure_configured()
        import resend
        resend.api_key = self.api_key

        params = {
            "from": self.from_email,
            "to": [to_email],
            "subject": subject,
            "text": body,
            "attachments": [
                {
                    "filename": attachment_filename,
                    "content": list(attachment_bytes),
                }
            ],
        }

        try:
            resp = resend.Emails.send(params)
            msg_id = resp.get("id") if isinstance(resp, dict) else getattr(resp, "id", str(resp))
            logger.info("Resend email with attachment sent successfully to %s, id: %s", to_email, msg_id)
            return {
                "id": str(msg_id),
                "provider": "resend",
                "recipient": to_email,
                "attachment": attachment_filename,
                "status": "sent",
            }
        except Exception as e:
            logger.error("Resend attachment email dispatch error: %s", str(e))
            raise EmailDispatchError(f"Resend dispatch with attachment failed: {str(e)}") from e

class MockEmailProvider(EmailProvider):
    """
    In-memory mock email provider for unit and integration testing.
    Records all dispatched messages and allows simulating failures.
    """

    def __init__(self, simulate_failure: bool = False, failure_message: str = "Simulated network failure"):
        self.sent_messages: List[Dict[str, Any]] = []
        self.simulate_failure = simulate_failure
        self.failure_message = failure_message

    def send_email(self, to_email: str, subject: str, body: str) -> Dict[str, Any]:
        if self.simulate_failure:
            raise EmailDispatchError(self.failure_message)

        record = {
            "id": f"mock-msg-{len(self.sent_messages) + 1}",
            "provider": "mock",
            "to": to_email,
            "subject": subject,
            "body": body,
            "attachment": None,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": "sent",
        }
        self.sent_messages.append(record)
        return record

    def send_email_with_attachment(
        self,
        to_email: str,
        subject: str,
        body: str,
        attachment_bytes: bytes,
        attachment_filename: str,
    ) -> Dict[str, Any]:
        if self.simulate_failure:
            raise EmailDispatchError(self.failure_message)

        record = {
            "id": f"mock-msg-{len(self.sent_messages) + 1}",
            "provider": "mock",
            "to": to_email,
            "subject": subject,
            "body": body,
            "attachment": attachment_filename,
            "attachment_size_bytes": len(attachment_bytes),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": "sent",
        }
        self.sent_messages.append(record)
        return record

    def clear(self):
        self.sent_messages.clear()

# Global default provider reference
_email_provider: Optional[EmailProvider] = None

def get_email_provider() -> EmailProvider:
    """
    Factory function returning configured EmailProvider.
    Respects settings.EMAIL_PROVIDER.
    """
    global _email_provider
    if _email_provider is not None:
        return _email_provider

    provider_name = settings.EMAIL_PROVIDER.strip().lower()
    if provider_name == "mock":
        _email_provider = MockEmailProvider()
    elif provider_name == "resend":
        _email_provider = ResendEmailProvider()
    else:
        # Default fallback to Resend
        _email_provider = ResendEmailProvider()

    return _email_provider

def set_email_provider(provider: Optional[EmailProvider]) -> None:
    """Helper to inject email provider (e.g. for testing)."""
    global _email_provider
    _email_provider = provider
