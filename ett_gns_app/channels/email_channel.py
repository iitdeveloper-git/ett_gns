import re
import smtplib
import time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import logging

from ett_gns_app.channels.base import NotificationChannel
from ett_gns_app.utils.helpers.template_helper import TemplateHelper
from ett_gns_app.config import AppConfig

logger = logging.getLogger(__name__)

# Valid email regex for recipient validation
EMAIL_REGEX = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"


class EmailChannel(NotificationChannel):
    def __init__(self, config: AppConfig):
        self.config = config
        self.smtp_server = config.smtp_server
        self.smtp_port = config.smtp_port
        self.smtp_auth_ident = config.smtp_auth_ident
        self.smtp_auth_password = config.smtp_auth_password
        self.from_email = config.smtp_auth_ident
        self.template_helper = TemplateHelper(config.template_dir)
        logger.info(f"EmailChannel initialized (Server: {self.smtp_server}:{self.smtp_port})")

    @property
    def channel_name(self) -> str:
        return "email"

    def validate(self, recipient: str) -> bool:
        return bool(re.match(EMAIL_REGEX, recipient))

    def send(self, recipient: str, subject: str, template_name: str, data: dict) -> None:
        if not self.validate(recipient):
            logger.error(f"Invalid email address: {recipient}")
            raise ValueError(f"Invalid email address: {recipient}")

        logger.info(f"Validating template: {template_name}")
        self.template_helper.validate_template(template_name, data)

        logger.info(f"Rendering template: {template_name}")
        html_content = self.template_helper.render_template(template_name, data)

        message = MIMEMultipart()
        message["From"] = self.from_email
        message["To"] = recipient
        message["Subject"] = subject
        message.attach(MIMEText(html_content, "html"))

        # Retry logic with exponential backoff
        max_retries = 3
        for attempt in range(max_retries):
            try:
                logger.info(f"Connecting to SMTP server (Attempt {attempt + 1}/{max_retries})")
                with smtplib.SMTP_SSL(self.smtp_server, self.smtp_port) as server:
                    # server.set_debuglevel(1) # uncomment for debug
                    server.login(self.smtp_auth_ident, self.smtp_auth_password)
                    server.send_message(message)
                logger.info(f"Email sent successfully to {recipient}")
                return
            except smtplib.SMTPException as e:
                logger.error(f"SMTP error on attempt {attempt + 1}: {str(e)}")
                if attempt == max_retries - 1:
                    raise ValueError(
                        f"Failed to send email after {max_retries} attempts. Error: {str(e)}"
                    )
                time.sleep(2**attempt)  # Backoff: 1s, 2s, 4s
            except Exception as e:
                logger.error(f"Unexpected error sending email: {str(e)}")
                raise ValueError(f"Failed to send email. Error: {str(e)}")
