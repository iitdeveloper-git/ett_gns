from ett_gns_app.email_service.email_notifications import EmailNotification
import logging

class GnsController:
    def __init__(self):
        # Channel mappings
        self.channels = {
            "email": EmailNotification(),
            # Other channels like 'sms' and 'whatsapp' can be added here
        }
        self.logger = logging.getLogger(__name__)
    def send_notification(self, channel_name, recipient, subject, template_name, data):
        """
        Sends a notification through the specified channel.
        
        :param channel_name: The name of the channel (e.g., 'email')
        :param recipient: The recipient's email or contact information
        :param subject: The subject of the notification (for email)
        :param template_name: The name of the template (must be an HTML file)
        :param data: Dictionary of dynamic data for template rendering
        """
        # Validation for required parameters
        required_params = {
            "channel_name": channel_name,
            "subject": subject,
            "recipient": recipient,
            "template_name": template_name
        }
        
        missing_keys = [key for key, value in required_params.items() if value is None or value == ""]
        if missing_keys:
            self.logger.error("Missing required parameters: %s", missing_keys)
            raise ValueError(f"Missing required parameters: {missing_keys}")
            
        if not template_name.endswith('.html'):
            self.logger.error("Invalid template format: %s", template_name)
            raise ValueError("Template name must be an HTML file.")

        # Check if the channel exists
        channel = self.channels.get(channel_name)
        if not channel:
            self.logger.error("Unsupported channel: %s", channel_name)
            raise ValueError(f"Channel '{channel_name}' is not supported.")

        # Send the notification via the selected channel
        self.logger.info("Sending notification via %s to %s", channel_name, recipient)
        channel.send(recipient, subject, template_name, data)
