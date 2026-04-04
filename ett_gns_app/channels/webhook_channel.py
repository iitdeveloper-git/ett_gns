import logging
import re
from ett_gns_app.channels.base import NotificationChannel

logger = logging.getLogger(__name__)

class WebhookChannel(NotificationChannel):
    def __init__(self, config=None):
        pass

    @property
    def channel_name(self) -> str:
        return "webhook"

    def validate(self, recipient: str) -> bool:
        # Validate if it looks like a URL
        url_regex = re.compile(
            r'^(?:http|ftp)s?://' # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|' #domain...
            r'localhost|' #localhost...
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})' # ...or ip
            r'(?::\d+)?' # optional port
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)
        return re.match(url_regex, recipient) is not None

    def send(self, recipient: str, subject: str, template_name: str, data: dict) -> None:
        logger.error(f"Webhook Channel is not implemented yet")
        raise NotImplementedError("Webhook Channel is currently not configured or implemented.")
