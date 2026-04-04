from abc import ABC, abstractmethod

class NotificationChannel(ABC):
    @abstractmethod
    def send(self, recipient: str, subject: str, template_name: str, data: dict) -> None:
        """Sends a notification to the recipient."""
        pass

    @abstractmethod
    def validate(self, recipient: str) -> bool:
        """Validates the recipient format for this channel."""
        pass

    @property
    @abstractmethod
    def channel_name(self) -> str:
        """Returns the specific channel name (e.g. 'email', 'sms')"""
        pass
