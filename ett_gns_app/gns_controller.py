import logging
import uuid
from concurrent.futures import ThreadPoolExecutor

from ett_gns_app.channels import EmailChannel, SmsChannel, WebhookChannel


class GnsController:
    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger(__name__)

        # ThreadPool for async sending
        self.executor = ThreadPoolExecutor(max_workers=10)

        # Initialize available channels
        self.channels = {
            "email": EmailChannel(config),
            "sms": SmsChannel(config),
            "webhook": WebhookChannel(config),
        }
        self.logger.info(f"GnsController initialized with {len(self.channels)} channels")

    def _async_send(
        self,
        channel,
        recipient: str,
        subject: str,
        template_name: str,
        data: dict,
        notification_id: str,
    ):
        """Internal task for async execution"""
        try:
            self.logger.info(f"[{notification_id}] Starting async send via {channel.channel_name}")
            channel.send(recipient, subject, template_name, data)
            self.logger.info(f"[{notification_id}] Async send completed via {channel.channel_name}")
        except Exception as e:
            self.logger.error(f"[{notification_id}] Async send failed: {str(e)}")

    def send_notification(
        self,
        channel_name: str,
        recipient: str,
        subject: str,
        template_name: str,
        data: dict,
        sync: bool = False,
    ) -> str:
        """
        Submits a notification to be sent asynchronously.
        Returns a unique notification ID.
        """
        # Validate required inputs
        params = {
            "channel_name": channel_name,
            "subject": subject,
            "recipient": recipient,
            "template_name": template_name,
        }
        missing_keys = [k for k, v in params.items() if not v]
        if missing_keys:
            self.logger.error(f"Missing required keys: {missing_keys}")
            raise ValueError(f"Missing required key value: {missing_keys}")

        if not template_name.endswith(".html"):
            raise ValueError("Template name must be an HTML file.")

        channel = self.channels.get(channel_name)
        if not channel:
            self.logger.error("Unsupported channel: %s", channel_name)
            raise ValueError(
                f"Channel '{channel_name}' is not supported. Available: {list(self.channels.keys())}"
            )

        notification_id = str(uuid.uuid4())

        self.logger.info(
            f"[{notification_id}] Enqueueing notification via {channel_name} to {recipient} (sync={sync})"
        )

        if sync:
            # Dispatch synchronously and await result
            try:
                self.logger.info(
                    f"[{notification_id}] Starting sync send via {channel.channel_name}"
                )
                channel.send(recipient, subject, template_name, data)
                self.logger.info(
                    f"[{notification_id}] Sync send completed via {channel.channel_name}"
                )
            except Exception as e:
                self.logger.error(f"[{notification_id}] Sync send failed: {str(e)}")
                raise e  # re-raise to be caught by route handler
        else:
            # Dispatch asynchronously
            self.executor.submit(
                self._async_send, channel, recipient, subject, template_name, data, notification_id
            )

        return notification_id
