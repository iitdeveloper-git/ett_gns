"""
Custom exception classes for the ETT GNS application.
"""
from typing import Optional, Dict, Any


class ETTBaseException(Exception):
    """Base exception class for ETT GNS application."""
    
    def __init__(
        self, 
        message: str, 
        error_code: Optional[str] = None, 
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code or self.__class__.__name__
        self.details = details or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for API responses."""
        return {
            "error": self.error_code,
            "message": self.message,
            "details": self.details
        }


class ValidationError(ETTBaseException):
    """Raised when input validation fails."""
    pass


class ConfigurationError(ETTBaseException):
    """Raised when configuration is invalid or missing."""
    pass


class TemplateError(ETTBaseException):
    """Raised when template operations fail."""
    pass


class EmailDeliveryError(ETTBaseException):
    """Raised when email delivery fails."""
    pass


class ChannelNotSupportedError(ETTBaseException):
    """Raised when an unsupported notification channel is requested."""
    pass


class RateLimitExceededError(ETTBaseException):
    """Raised when rate limit is exceeded."""
    pass


class AuthenticationError(ETTBaseException):
    """Raised when authentication fails."""
    pass


class TemplateNotFoundError(TemplateError):
    """Raised when a template is not found."""
    pass


class TemplateMissingVariablesError(TemplateError):
    """Raised when required template variables are missing."""
    pass


class SMTPConnectionError(EmailDeliveryError):
    """Raised when SMTP connection fails."""
    pass


class InvalidEmailFormatError(ValidationError):
    """Raised when email format is invalid."""
    pass


class PayloadTooLargeError(ValidationError):
    """Raised when request payload exceeds size limit."""
    pass