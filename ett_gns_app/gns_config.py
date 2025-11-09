import os
from dotenv import load_dotenv
import logging

# Load environment variables from .env file
load_dotenv()
class AppConfig:
    def __init__(self) -> None:
        self.config = {}
        self.template_dir = os.getenv("TEMPLATE_DIR", "templates")
        logger = logging.getLogger(__name__)\
        # Log the template directory being used
        logger.info("Using template directory: %s", self.template_dir)