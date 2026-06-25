import logging
from ett_gns_app.channels.base import NotificationChannel

logger = logging.getLogger(__name__)


class SmsChannel(NotificationChannel):
    def __init__(self, config=None):
        pass

    @property
    def channel_name(self) -> str:
        return "sms"

    def validate(self, recipient: str) -> bool:
        # Example naive validation: just checking if it contains digits
        return any(char.isdigit() for char in recipient)

    def send(self, recipient: str, subject: str, template_name: str, data: dict) -> None:
        logger.error(f"SMS Channel is not implemented yet")
        raise NotImplementedError("SMS Channel is currently not configured or implemented.")
