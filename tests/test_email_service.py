"""
Comprehensive test suite for the ETT GNS email service.
"""
import unittest
from unittest.mock import Mock, patch, MagicMock
import json
import tempfile
import os
from pathlib import Path

# Test imports
from ett_gns_app import create_app
from ett_gns_app.core.config import AppConfig, SMTPConfig, ConfigManager
from ett_gns_app.core.exceptions import (
    ValidationError, EmailDeliveryError, TemplateNotFoundError,
    TemplateMissingVariablesError, InvalidEmailFormatError
)
from ett_gns_app.core.validation import RequestValidator
from ett_gns_app.email_service.email_notifications import EmailNotification
from ett_gns_app.gns_controller import GnsController
from ett_gns_app.utils.helpers.template_helper import TemplateHelper


class TestConfigManager(unittest.TestCase):
    """Test configuration management."""
    
    def setUp(self):
        self.config_manager = ConfigManager()
    
    def test_smtp_config_validation(self):
        """Test SMTP configuration validation."""
        # Valid configuration
        valid_config = SMTPConfig(
            server="smtp.example.com",
            port=587,
            auth_ident="test@example.com",
            auth_password="password"
        )
        self.assertEqual(valid_config.server, "smtp.example.com")
        
        # Invalid port
        with self.assertRaises(ValueError):
            SMTPConfig(
                server="smtp.example.com",
                port=70000,  # Invalid port
                auth_ident="test@example.com",
                auth_password="password"
            )
        
        # Missing required fields
        with self.assertRaises(ValueError):
            SMTPConfig(
                server="",  # Empty server
                port=587,
                auth_ident="test@example.com",
                auth_password="password"
            )
    
    @patch.dict(os.environ, {
        'SMTP_SERVER': 'smtp.test.com',
        'SMTP_PORT': '587',
        'SMTP_AUTH_IDENT': 'test@test.com',
        'SMTP_AUTH_PASSWORD': 'testpass',
        'FLASK_ENV': 'testing'
    })
    def test_config_loading_from_env(self):
        """Test configuration loading from environment variables."""
        config = self.config_manager.load_config()
        
        self.assertEqual(config.smtp.server, 'smtp.test.com')
        self.assertEqual(config.smtp.port, 587)
        self.assertEqual(config.smtp.auth_ident, 'test@test.com')
        self.assertEqual(config.environment, 'testing')


class TestRequestValidator(unittest.TestCase):
    """Test request validation."""
    
    def test_valid_notification_request(self):
        """Test validation of valid notification request."""
        valid_payload = {
            "channel_name": "email",
            "recipient": "test@example.com",
            "subject": "Test Subject",
            "template_name": "welcome_email.html",
            "data": {"user_name": "John Doe", "welcome_message": "Welcome!"}
        }
        
        result = RequestValidator.validate_send_notification(valid_payload)
        self.assertEqual(result["recipient"], "test@example.com")
        self.assertEqual(result["channel_name"], "email")
    
    def test_missing_required_fields(self):
        """Test validation with missing required fields."""
        invalid_payload = {
            "channel_name": "email",
            # Missing recipient, subject, template_name
        }
        
        with self.assertRaises(ValidationError) as context:
            RequestValidator.validate_send_notification(invalid_payload)
        
        self.assertIn("recipient", str(context.exception))
        self.assertIn("subject", str(context.exception))
    
    def test_invalid_email_format(self):
        """Test validation with invalid email format."""
        invalid_payload = {
            "channel_name": "email",
            "recipient": "invalid-email",  # Invalid email
            "subject": "Test Subject",
            "template_name": "welcome_email.html"
        }
        
        with self.assertRaises(ValidationError) as context:
            RequestValidator.validate_send_notification(invalid_payload)
        
        self.assertIn("valid email address", str(context.exception))
    
    def test_invalid_template_name(self):
        """Test validation with invalid template name."""
        invalid_payload = {
            "channel_name": "email",
            "recipient": "test@example.com",
            "subject": "Test Subject",
            "template_name": "invalid_template.txt"  # Not .html
        }
        
        with self.assertRaises(ValidationError) as context:
            RequestValidator.validate_send_notification(invalid_payload)
        
        self.assertIn("HTML template name", str(context.exception))
    
    def test_unsupported_channel(self):
        """Test validation with unsupported channel."""
        invalid_payload = {
            "channel_name": "sms",  # Not supported yet
            "recipient": "test@example.com",
            "subject": "Test Subject",
            "template_name": "welcome_email.html"
        }
        
        with self.assertRaises(ValidationError) as context:
            RequestValidator.validate_send_notification(invalid_payload)
        
        self.assertIn("must be one of: email", str(context.exception))
    
    def test_template_data_sanitization(self):
        """Test sanitization of template data."""
        dangerous_data = {
            "user_name": "<script>alert('xss')</script>",
            "message": "Hello & welcome",
            "link": "http://example.com/test?param=value&other=<script>"
        }
        
        sanitized = RequestValidator.sanitize_template_data(dangerous_data)
        
        self.assertEqual(sanitized["user_name"], "&lt;script&gt;alert(&#x27;xss&#x27;)&lt;&#x2F;script&gt;")
        self.assertEqual(sanitized["message"], "Hello &amp; welcome")
        self.assertNotIn("<script>", sanitized["link"])


class TestTemplateHelper(unittest.TestCase):
    """Test template helper functionality."""
    
    def setUp(self):
        # Create temporary template directory
        self.temp_dir = tempfile.mkdtemp()
        
        # Create test templates
        welcome_template = """
        <html>
        <body>
            <h1>Welcome, {{ user_name }}!</h1>
            <p>{{ welcome_message }}</p>
        </body>
        </html>
        """
        
        with open(os.path.join(self.temp_dir, "welcome_email.html"), "w") as f:
            f.write(welcome_template)
        
        self.helper = TemplateHelper(self.temp_dir)
    
    def tearDown(self):
        # Clean up temporary directory
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_valid_template_rendering(self):
        """Test rendering of valid template with data."""
        data = {
            "user_name": "John Doe",
            "welcome_message": "Welcome to our platform!"
        }
        
        # Mock the templates data
        self.helper.templates = {
            "welcome_email.html": ["user_name", "welcome_message"]
        }
        
        result = self.helper.render_template("welcome_email.html", data)
        
        self.assertIn("John Doe", result)
        self.assertIn("Welcome to our platform!", result)
    
    def test_missing_template_variables(self):
        """Test validation with missing template variables."""
        data = {
            "user_name": "John Doe"
            # Missing welcome_message
        }
        
        # Mock the templates data
        self.helper.templates = {
            "welcome_email.html": ["user_name", "welcome_message"]
        }
        
        with self.assertRaises(ValueError) as context:
            self.helper.validate_template("welcome_email.html", data)
        
        self.assertIn("Missing variables", str(context.exception))
        self.assertIn("welcome_message", str(context.exception))
    
    def test_template_not_found(self):
        """Test handling of non-existent template."""
        data = {"user_name": "John Doe"}
        
        with self.assertRaises(ValueError) as context:
            self.helper.validate_template("nonexistent.html", data)
        
        self.assertIn("not available", str(context.exception))


class TestEmailNotification(unittest.TestCase):
    """Test email notification functionality."""
    
    def setUp(self):
        # Mock configuration
        self.mock_config = Mock()
        self.mock_config.smtp_server = "smtp.test.com"
        self.mock_config.smtp_port = 587
        self.mock_config.smtp_auth_ident = "test@test.com"
        self.mock_config.from_email = "test@test.com"
        self.mock_config.smtp_auth_password = "password"
        self.mock_config.template_dir = "templates"
        
        with patch('ett_gns_app.email_service.email_notifications.EmailConfig') as mock_email_config:
            mock_email_config.return_value = self.mock_config
            with patch('ett_gns_app.email_service.email_notifications.TemplateHelper') as mock_template_helper:
                self.mock_template_helper = Mock()
                mock_template_helper.return_value = self.mock_template_helper
                
                self.email_notification = EmailNotification()
    
    @patch('ett_gns_app.email_service.email_notifications.smtplib.SMTP_SSL')
    def test_successful_email_send(self, mock_smtp):
        """Test successful email sending."""
        # Setup mocks
        mock_server = Mock()
        mock_smtp.return_value.__enter__.return_value = mock_server
        
        self.mock_template_helper.render_template.return_value = "<html><body>Test</body></html>"
        
        # Send email
        self.email_notification.send(
            "test@example.com",
            "Test Subject",
            "welcome_email.html",
            {"user_name": "John"}
        )
        
        # Verify SMTP calls
        mock_smtp.assert_called_once_with("smtp.test.com", 587)
        mock_server.login.assert_called_once_with("test@test.com", "password")
        mock_server.send_message.assert_called_once()
    
    def test_invalid_email_address(self):
        """Test handling of invalid email address."""
        with self.assertRaises(ValueError) as context:
            self.email_notification.send(
                "invalid-email",
                "Test Subject",
                "welcome_email.html",
                {"user_name": "John"}
            )
        
        self.assertIn("Invalid email address", str(context.exception))
    
    @patch('ett_gns_app.email_service.email_notifications.smtplib.SMTP_SSL')
    def test_smtp_connection_failure(self, mock_smtp):
        """Test handling of SMTP connection failure."""
        # Setup mock to raise exception
        mock_smtp.side_effect = Exception("Connection failed")
        
        self.mock_template_helper.render_template.return_value = "<html><body>Test</body></html>"
        
        with self.assertRaises(ValueError) as context:
            self.email_notification.send(
                "test@example.com",
                "Test Subject",
                "welcome_email.html",
                {"user_name": "John"}
            )
        
        self.assertIn("Failed to send email", str(context.exception))


class TestGnsController(unittest.TestCase):
    """Test GNS controller functionality."""
    
    def setUp(self):
        self.controller = GnsController()
    
    def test_valid_notification_sending(self):
        """Test sending notification through valid channel."""
        # Mock the email channel
        mock_email_channel = Mock()
        self.controller.channels["email"] = mock_email_channel
        
        self.controller.send_notification(
            channel_name="email",
            recipient="test@example.com",
            subject="Test Subject",
            template_name="welcome_email.html",
            data={"user_name": "John"}
        )
        
        mock_email_channel.send.assert_called_once_with(
            "test@example.com",
            "Test Subject",
            "welcome_email.html",
            {"user_name": "John"}
        )
    
    def test_missing_required_parameters(self):
        """Test handling of missing required parameters."""
        with self.assertRaises(ValueError) as context:
            self.controller.send_notification(
                channel_name=None,  # Missing
                recipient="test@example.com",
                subject="Test Subject",
                template_name="welcome_email.html",
                data={}
            )
        
        self.assertIn("Missing required parameters", str(context.exception))
    
    def test_unsupported_channel(self):
        """Test handling of unsupported channel."""
        with self.assertRaises(ValueError) as context:
            self.controller.send_notification(
                channel_name="sms",  # Not supported
                recipient="test@example.com",
                subject="Test Subject",
                template_name="welcome_email.html",
                data={}
            )
        
        self.assertIn("not supported", str(context.exception))
    
    def test_invalid_template_format(self):
        """Test handling of invalid template format."""
        with self.assertRaises(ValueError) as context:
            self.controller.send_notification(
                channel_name="email",
                recipient="test@example.com",
                subject="Test Subject",
                template_name="template.txt",  # Not .html
                data={}
            )
        
        self.assertIn("HTML file", str(context.exception))


class TestFlaskApp(unittest.TestCase):
    """Test Flask application endpoints."""
    
    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()
    
    def test_home_endpoint(self):
        """Test home endpoint."""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertIn("Welcome to the ETT Service", data["message"])
    
    def test_health_check_endpoint(self):
        """Test health check endpoint."""
        response = self.client.get('/health')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertEqual(data["status"], "healthy")
    
    @patch('ett_gns_app.gns_controller.GnsController.send_notification')
    def test_send_notification_endpoint_success(self, mock_send):
        """Test successful notification sending via API."""
        payload = {
            "channel_name": "email",
            "recipient": "test@example.com",
            "subject": "Test Subject",
            "template_name": "welcome_email.html",
            "data": {"user_name": "John Doe", "welcome_message": "Welcome!"}
        }
        
        response = self.client.post(
            '/send_notification',
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn("successfully", data["message"])
        
        mock_send.assert_called_once()
    
    def test_send_notification_endpoint_invalid_payload(self):
        """Test notification endpoint with invalid payload."""
        invalid_payload = {
            "channel_name": "email",
            # Missing required fields
        }
        
        response = self.client.post(
            '/send_notification',
            data=json.dumps(invalid_payload),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
    
    def test_404_error_handler(self):
        """Test 404 error handler."""
        response = self.client.get('/nonexistent')
        self.assertEqual(response.status_code, 404)
        
        data = json.loads(response.data)
        self.assertEqual(data["error"], "Not Found")


if __name__ == '__main__':
    # Create test suite
    test_suite = unittest.TestSuite()
    
    # Add test cases
    test_classes = [
        TestConfigManager,
        TestRequestValidator,
        TestTemplateHelper,
        TestEmailNotification,
        TestGnsController,
        TestFlaskApp
    ]
    
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        test_suite.addTests(tests)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # Exit with error code if tests failed
    exit(0 if result.wasSuccessful() else 1)