import os
from dataclasses import dataclass
from dotenv import load_dotenv
import logging

logger = logging.getLogger(__name__)


@dataclass
class AppConfig:
    smtp_server: str
    smtp_port: int
    smtp_auth_ident: str
    smtp_auth_password: str
    smtp_auth_name: str
    template_dir: str
    flask_env: str
    port: int


def load_config() -> AppConfig:
    """Loads configuration from environment variables."""
    # Ensure env is loaded
    load_dotenv()

    port_str = os.getenv("SMTP_PORT", "465")
    try:
        smtp_port = int(port_str)
    except ValueError:
        logger.warning(f"Invalid SMTP_PORT '{port_str}', defaulting to 465")
        smtp_port = 465

    app_port_str = os.getenv("PORT", "5000")
    try:
        app_port = int(app_port_str)
    except ValueError:
        logger.warning(f"Invalid PORT '{app_port_str}', defaulting to 5000")
        app_port = 5000

    config = AppConfig(
        smtp_server=os.getenv("SMTP_SERVER", ""),
        smtp_port=smtp_port,
        smtp_auth_ident=os.getenv("SMTP_AUTH_IDENT", ""),
        smtp_auth_password=os.getenv("SMTP_AUTH_PASSWORD", ""),
        smtp_auth_name=os.getenv("SMTP_AUTH_NAME", ""),
        template_dir=os.getenv("TEMPLATE_DIR", "templates"),
        flask_env=os.getenv("FLASK_ENV", "development"),
        port=app_port,
    )

    logger.info("Configuration loaded successfully")
    return config
