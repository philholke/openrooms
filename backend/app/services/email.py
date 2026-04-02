"""
Email rendering and delivery service.

In development mode (EMAIL_ENABLED=False), emails are rendered fully
(to catch template errors early) but logged to stdout instead of sent.
In production mode, emails are sent via aiosmtplib.
"""

import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from html import escape
from pathlib import Path
from re import sub as re_sub

import aiosmtplib
from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.core.config import settings

logger = logging.getLogger(__name__)

_TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates" / "email"


class EmailService:
    """Renders Jinja2 email templates and sends via SMTP (or logs in dev)."""

    def __init__(self) -> None:
        self.enabled = settings.EMAIL_ENABLED
        self.jinja_env = Environment(
            loader=FileSystemLoader(str(_TEMPLATE_DIR)),
            autoescape=select_autoescape(["html"]),
        )
        # Inject global template variables
        self.jinja_env.globals["app_base_url"] = settings.APP_BASE_URL

    async def send(
        self,
        *,
        to: str,
        subject: str,
        template: str,
        context: dict,
    ) -> bool:
        """
        Render a template and send (or log) the email.

        Returns True if the email was sent via SMTP, False if dev-logged.
        """
        html = self._render(template, context)
        plain = self._html_to_plain(html)

        if not self.enabled:
            logger.info(
                "[EMAIL-DEV] To: %s | Subject: %s\n%s",
                to,
                subject,
                plain[:500],
            )
            return False

        await self._smtp_send(to, subject, html, plain)
        return True

    def _render(self, template_name: str, context: dict) -> str:
        """Render a Jinja2 template to HTML string."""
        tmpl = self.jinja_env.get_template(f"{template_name}.html")
        return tmpl.render(**context)

    @staticmethod
    def _html_to_plain(html: str) -> str:
        """Crude HTML-to-plaintext conversion for the text/plain fallback."""
        # Strip tags, collapse whitespace
        text = re_sub(r"<br\s*/?>", "\n", html)
        text = re_sub(r"<[^>]+>", "", text)
        text = re_sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    @staticmethod
    def _sanitize_header(value: str) -> str:
        """Strip CR/LF characters to prevent email header injection."""
        return re_sub(r"[\r\n]", "", value)

    async def _smtp_send(
        self,
        to: str,
        subject: str,
        html: str,
        plain: str,
    ) -> None:
        """Send a multipart email via aiosmtplib."""
        msg = MIMEMultipart("alternative")
        msg["Subject"] = self._sanitize_header(subject)
        msg["From"] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL}>"
        msg["To"] = self._sanitize_header(to)

        msg.attach(MIMEText(plain, "plain", "utf-8"))
        msg.attach(MIMEText(html, "html", "utf-8"))

        await aiosmtplib.send(
            msg,
            hostname=settings.SMTP_HOST,
            port=settings.SMTP_PORT,
            username=settings.SMTP_USER or None,
            password=settings.SMTP_PASSWORD or None,
            use_tls=settings.SMTP_USE_TLS,
        )
        logger.info("Email sent to %s: %s", to, subject)


# Module-level singleton
email_service = EmailService()
