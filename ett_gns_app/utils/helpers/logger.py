"""
Enhanced logging system with structured logging, correlation IDs, and multiple output formats.
"""
import logging
import logging.handlers
import json
import uuid
import contextvars
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path
import colorlog
from ett_gns_app.core.config import get_config


# Correlation ID context variable for tracking requests
correlation_id: contextvars.ContextVar[str] = contextvars.ContextVar('correlation_id', default='')


class CorrelationFilter(logging.Filter):
    """Filter to add correlation ID to log records."""
    
    def filter(self, record):
        record.correlation_id = correlation_id.get('')
        return True


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging."""
    
    def format(self, record):
        log_entry = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'level': record.levelname,
            'logger': record.name,
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
            'message': record.getMessage(),
            'correlation_id': getattr(record, 'correlation_id', ''),
        }
        
        # Add exception info if present
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)
        
        # Add extra fields
        for key, value in record.__dict__.items():
            if key not in ['name', 'msg', 'args', 'levelname', 'levelno', 'pathname', 
                          'filename', 'module', 'exc_info', 'exc_text', 'stack_info',
                          'lineno', 'funcName', 'created', 'msecs', 'relativeCreated',
                          'thread', 'threadName', 'processName', 'process', 'getMessage',
                          'correlation_id']:
                log_entry[key] = value
        
        return json.dumps(log_entry)


class LoggerManager:
    """Centralized logger management."""
    
    _loggers: Dict[str, logging.Logger] = {}
    _configured = False
    
    @classmethod
    def setup_logging(cls, config=None):
        """Setup application-wide logging configuration."""
        if cls._configured:
            return
        
        if config is None:
            try:
                config = get_config()
            except Exception:
                # Fallback configuration if config loading fails
                config = type('Config', (), {
                    'log_level': 'INFO',
                    'environment': 'development',
                    'debug': False
                })()
        
        # Create logs directory
        log_dir = Path('logs')
        log_dir.mkdir(exist_ok=True)
        
        # Configure root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(getattr(logging, config.log_level))
        
        # Clear existing handlers
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
        
        # Add correlation filter to all handlers
        correlation_filter = CorrelationFilter()
        
        # Console handler with colors (for development)
        if config.environment == 'development' or config.debug:
            console_handler = colorlog.StreamHandler()
            console_handler.setLevel(getattr(logging, config.log_level))
            
            color_formatter = colorlog.ColoredFormatter(
                '%(asctime)s | %(log_color)s%(levelname)-8s%(reset)s | '
                '%(correlation_id)s | %(name)s:%(funcName)s:%(lineno)d | %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S',
                log_colors={
                    'DEBUG': 'cyan',
                    'INFO': 'green',
                    'WARNING': 'yellow',
                    'ERROR': 'red',
                    'CRITICAL': 'red,bg_white',
                }
            )
            console_handler.setFormatter(color_formatter)
            console_handler.addFilter(correlation_filter)
            root_logger.addHandler(console_handler)
        
        # File handler for all logs
        file_handler = logging.handlers.RotatingFileHandler(
            log_dir / 'app.log',
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5
        )
        file_handler.setLevel(logging.INFO)
        
        if config.environment == 'production':
            # Use JSON formatter for production
            file_formatter = JSONFormatter()
        else:
            # Use standard formatter for development/testing
            file_formatter = logging.Formatter(
                '%(asctime)s | %(levelname)-8s | %(correlation_id)s | '
                '%(name)s:%(funcName)s:%(lineno)d | %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
        
        file_handler.setFormatter(file_formatter)
        file_handler.addFilter(correlation_filter)
        root_logger.addHandler(file_handler)
        
        # Error file handler
        error_handler = logging.handlers.RotatingFileHandler(
            log_dir / 'error.log',
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(file_formatter)
        error_handler.addFilter(correlation_filter)
        root_logger.addHandler(error_handler)
        
        cls._configured = True
    
    @classmethod
    def get_logger(cls, name: str) -> logging.Logger:
        """Get or create a logger with the given name."""
        if name not in cls._loggers:
            if not cls._configured:
                cls.setup_logging()
            
            logger = logging.getLogger(name)
            cls._loggers[name] = logger
        
        return cls._loggers[name]


def setup_logger(name: Optional[str] = None) -> logging.Logger:
    """Setup and return a logger instance."""
    if name is None:
        name = __name__
    
    return LoggerManager.get_logger(name)


def set_correlation_id(request_id: Optional[str] = None) -> str:
    """Set correlation ID for request tracking."""
    if request_id is None:
        request_id = str(uuid.uuid4())
    
    correlation_id.set(request_id)
    return request_id


def get_correlation_id() -> str:
    """Get current correlation ID."""
    return correlation_id.get('')


def log_request(logger: logging.Logger, method: str, path: str, **kwargs):
    """Log HTTP request with structured data."""
    logger.info(
        "HTTP Request",
        extra={
            'request_method': method,
            'request_path': path,
            'event_type': 'http_request',
            **kwargs
        }
    )


def log_response(logger: logging.Logger, status_code: int, duration_ms: float, **kwargs):
    """Log HTTP response with structured data."""
    logger.info(
        "HTTP Response",
        extra={
            'response_status': status_code,
            'response_duration_ms': duration_ms,
            'event_type': 'http_response',
            **kwargs
        }
    )


def log_email_sent(logger: logging.Logger, recipient: str, template: str, **kwargs):
    """Log email sent event with structured data."""
    logger.info(
        "Email sent successfully",
        extra={
            'recipient': recipient,
            'template': template,
            'event_type': 'email_sent',
            **kwargs
        }
    )


def log_email_failed(logger: logging.Logger, recipient: str, template: str, error: str, **kwargs):
    """Log email failure event with structured data."""
    logger.error(
        "Email sending failed",
        extra={
            'recipient': recipient,
            'template': template,
            'error': error,
            'event_type': 'email_failed',
            **kwargs
        }
    )
