import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class EmailConfig:
    def __init__(self):
        self.smtp_server = os.getenv("SMTP_SERVER", "server")
        self.smtp_port = int(os.getenv("SMTP_PORT", "port"))  # Convert to int
        self.smtp_auth_ident = os.getenv("SMTP_AUTH_IDENT", "your_email@gmail.com")
        self.smtp_auth_password = os.getenv("SMTP_AUTH_PASSWORD", "your_password")
        self.from_email = self.smtp_auth_ident
        self.template_dir = os.getenv("TEMPLATE_DIR", "templates") # move to email_service.config to app_config