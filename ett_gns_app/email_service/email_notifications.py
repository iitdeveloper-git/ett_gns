import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from ett_gns_app.email_service.constant import is_valid_email
from ett_gns_app.email_service.config import EmailConfig
from ett_gns_app.utils.helpers.template_helper import TemplateHelper
from ett_gns_app.utils.helpers.logger import setup_logger

# Set up the logger
logger = setup_logger()

class EmailNotification:
    def __init__(self):
        email_config = EmailConfig()
        self.smtp_server = email_config.smtp_server
        self.smtp_port = email_config.smtp_port
        self.smtp_auth_ident = email_config.smtp_auth_ident
        self.from_email = email_config.from_email
        self.smtp_auth_password = email_config.smtp_auth_password
        template_dir = email_config.template_dir
        self.template_helper = TemplateHelper(template_dir)
        logger.info("EmailNotification initialized with SMTP server: %s", self.smtp_server)

    def send(self, recipient_email, subject, template_name, data):
        """
        Sends an email notification using the SMTP protocol.
        :param recipient_email: The recipient's email address
        :param subject: The subject of the email
        :param template_name: The email template name
        :param data: Dynamic data to render the template
        """
        # Validate the recipient email format
        if not is_valid_email(recipient_email):
            logger.error("Invalid email address: %s", recipient_email)
            raise ValueError(f"Invalid email address: {recipient_email}")
        
        # Validate the template and required variables
        logger.info("Validating template: %s", template_name)
        self.template_helper.validate_template(template_name, data)

        # Render the email template
        logger.info("Rendering template: %s", template_name)
        html_content = self.template_helper.render_template(template_name, data)

        # Compose and send the email
        message = MIMEMultipart()
        message['From'] = self.from_email
        message['To'] = recipient_email
        message['Subject'] = subject
        message.attach(MIMEText(html_content, 'html'))

        try:
            with smtplib.SMTP_SSL(self.smtp_server, self.smtp_port) as server:
                logger.info("Connecting to SMTP server: %s", self.smtp_server)
                server.login(self.smtp_auth_ident, self.smtp_auth_password)
                server.send_message(message)
                logger.info("Email sent successfully to %s", recipient_email)
        
        except Exception as e:
            logger.error("Failed to send email to %s. Error: %s", recipient_email, str(e))
            raise ValueError(f"Failed to send email. Error: {str(e)}")
