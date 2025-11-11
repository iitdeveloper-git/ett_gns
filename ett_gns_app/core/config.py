"""
Centralized configuration management with validation and type safety.
"""
import os
import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass, field
from dotenv import load_dotenv


@dataclass
class SMTPConfig:
    """SMTP server configuration."""
    server: str
    port: int
    auth_ident: str
    auth_password: str
    auth_name: str = "ETT Service"
    use_tls: bool = True
    timeout: int = 30

    def __post_init__(self):
        """Validate SMTP configuration."""
        if not self.server:
            raise ValueError("SMTP server is required")
        if not (1 <= self.port <= 65535):
            raise ValueError("SMTP port must be between 1 and 65535")
        if not self.auth_ident:
            raise ValueError("SMTP authentication identity is required")
        if not self.auth_password:
            raise ValueError("SMTP authentication password is required")


@dataclass
class AppConfig:
    """Main application configuration."""
    debug: bool = False
    host: str = "0.0.0.0"
    port: int = 5000
    secret_key: str = field(default_factory=lambda: os.urandom(32).hex())
    environment: str = "development"
    template_dir: str = "templates"
    log_level: str = "INFO"
    max_content_length: int = 16 * 1024 * 1024  # 16MB
    
    # Email configuration
    smtp: Optional[SMTPConfig] = None
    
    # Security settings
    rate_limit_per_minute: int = 60
    rate_limit_per_hour: int = 1000
    
    # Monitoring
    enable_metrics: bool = True
    health_check_timeout: int = 5

    def __post_init__(self):
        """Validate application configuration."""
        if self.environment not in ["development", "testing", "production"]:
            raise ValueError("Environment must be one of: development, testing, production")
        
        if self.log_level not in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
            raise ValueError("Invalid log level")
        
        if not (1 <= self.port <= 65535):
            raise ValueError("Port must be between 1 and 65535")


class ConfigManager:
    """Configuration manager with environment variable loading and validation."""
    
    def __init__(self, env_file: Optional[str] = None):
        self.logger = logging.getLogger(__name__)
        
        # Load environment variables
        if env_file:
            load_dotenv(env_file)
        else:
            load_dotenv()
        
        self._config: Optional[AppConfig] = None
    
    def load_config(self) -> AppConfig:
        """Load and validate configuration from environment variables."""
        if self._config is not None:
            return self._config
        
        try:
            # Load SMTP configuration
            smtp_config = SMTPConfig(
                server=self._get_env("SMTP_SERVER", required=True),
                port=int(self._get_env("SMTP_PORT", "465")),
                auth_ident=self._get_env("SMTP_AUTH_IDENT", required=True),
                auth_password=self._get_env("SMTP_AUTH_PASSWORD", required=True),
                auth_name=self._get_env("SMTP_AUTH_NAME", "ETT Service"),
                use_tls=self._get_env("SMTP_USE_TLS", "true").lower() == "true",
                timeout=int(self._get_env("SMTP_TIMEOUT", "30"))
            )
            
            # Load application configuration
            self._config = AppConfig(
                debug=self._get_env("FLASK_DEBUG", "false").lower() == "true",
                host=self._get_env("HOST", "0.0.0.0"),
                port=int(self._get_env("PORT", "5000")),
                secret_key=self._get_env("SECRET_KEY", os.urandom(32).hex()),
                environment=self._get_env("FLASK_ENV", "development"),
                template_dir=self._get_env("TEMPLATE_DIR", "templates"),
                log_level=self._get_env("LOG_LEVEL", "INFO").upper(),
                max_content_length=int(self._get_env("MAX_CONTENT_LENGTH", str(16 * 1024 * 1024))),
                smtp=smtp_config,
                rate_limit_per_minute=int(self._get_env("RATE_LIMIT_PER_MINUTE", "60")),
                rate_limit_per_hour=int(self._get_env("RATE_LIMIT_PER_HOUR", "1000")),
                enable_metrics=self._get_env("ENABLE_METRICS", "true").lower() == "true",
                health_check_timeout=int(self._get_env("HEALTH_CHECK_TIMEOUT", "5"))
            )
            
            self.logger.info("Configuration loaded successfully")
            self.logger.info("Environment: %s", self._config.environment)
            self.logger.info("Debug mode: %s", self._config.debug)
            self.logger.info("Template directory: %s", self._config.template_dir)
            
            return self._config
            
        except Exception as e:
            self.logger.error("Failed to load configuration: %s", str(e))
            raise
    
    def get_config(self) -> AppConfig:
        """Get the current configuration, loading it if necessary."""
        if self._config is None:
            return self.load_config()
        return self._config
    
    def _get_env(self, key: str, default: Optional[str] = None, required: bool = False) -> str:
        """Get environment variable with validation."""
        value = os.getenv(key, default)
        
        if required and not value:
            raise ValueError(f"Required environment variable '{key}' is not set")
        
        return value or ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary for serialization."""
        config = self.get_config()
        return {
            "debug": config.debug,
            "host": config.host,
            "port": config.port,
            "environment": config.environment,
            "template_dir": config.template_dir,
            "log_level": config.log_level,
            "max_content_length": config.max_content_length,
            "rate_limit_per_minute": config.rate_limit_per_minute,
            "rate_limit_per_hour": config.rate_limit_per_hour,
            "enable_metrics": config.enable_metrics,
            "health_check_timeout": config.health_check_timeout,
            "smtp": {
                "server": config.smtp.server if config.smtp else None,
                "port": config.smtp.port if config.smtp else None,
                "use_tls": config.smtp.use_tls if config.smtp else None,
                "timeout": config.smtp.timeout if config.smtp else None,
                # Exclude sensitive data
                "auth_ident": "***" if config.smtp and config.smtp.auth_ident else None,
                "auth_password": "***" if config.smtp and config.smtp.auth_password else None,
            }
        }


# Global configuration instance
config_manager = ConfigManager()


def get_config() -> AppConfig:
    """Get the application configuration."""
    return config_manager.get_config()