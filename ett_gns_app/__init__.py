"""
ETT GNS Application Factory
"""
from flask import Flask, jsonify, request
import logging
from ett_gns_app.gns_routes import register_blueprints
from ett_gns_app.core.config import get_config
from ett_gns_app.core.exceptions import (
    ETTBaseException, ValidationError, RateLimitExceededError,
    AuthenticationError, ConfigurationError
)
from ett_gns_app.core.security import request_logging_middleware
from ett_gns_app.utils.helpers.logger import LoggerManager, setup_logger


def create_app(config_override=None):
    """Create and configure Flask application."""
    
    # Initialize Flask app
    app = Flask(__name__)
    
    try:
        # Load configuration
        if config_override:
            app.config.update(config_override)
        else:
            config = get_config()
            app.config.update({
                'SECRET_KEY': config.secret_key,
                'DEBUG': config.debug,
                'MAX_CONTENT_LENGTH': config.max_content_length,
                'TESTING': config.environment == 'testing'
            })
        
        # Setup logging
        LoggerManager.setup_logging(config if not config_override else None)
        logger = setup_logger(__name__)
        
        logger.info("Starting ETT GNS Application")
        logger.info("Environment: %s", config.environment if not config_override else "custom")
        
        # Register request logging middleware
        before_request, after_request = request_logging_middleware()
        app.before_request(before_request)
        app.after_request(after_request)
        
        # Register blueprints
        register_blueprints(app)
        
        # Register error handlers
        register_error_handlers(app, logger)
        
        logger.info("ETT GNS Application initialized successfully")
        
    except Exception as e:
        # Fallback logger if main logging setup fails
        fallback_logger = logging.getLogger(__name__)
        fallback_logger.error("Failed to initialize application: %s", str(e))
        raise ConfigurationError(f"Application initialization failed: {str(e)}")
    
    return app


def register_error_handlers(app: Flask, logger: logging.Logger):
    """Register application error handlers."""
    
    @app.errorhandler(ValidationError)
    def handle_validation_error(e):
        logger.warning("Validation error: %s", str(e))
        return jsonify(e.to_dict()), 400
    
    @app.errorhandler(RateLimitExceededError)
    def handle_rate_limit_error(e):
        logger.warning("Rate limit exceeded: %s", str(e))
        response = jsonify(e.to_dict())
        
        # Add rate limit headers
        if e.details:
            response.headers['X-RateLimit-Limit'] = str(e.details.get('limit', ''))
            response.headers['X-RateLimit-Remaining'] = str(e.details.get('remaining', 0))
            response.headers['X-RateLimit-Reset'] = str(e.details.get('reset_time', ''))
            response.headers['Retry-After'] = str(e.details.get('retry_after', 60))
        
        return response, 429
    
    @app.errorhandler(AuthenticationError)
    def handle_auth_error(e):
        logger.warning("Authentication error: %s", str(e))
        return jsonify(e.to_dict()), 401
    
    @app.errorhandler(ETTBaseException)
    def handle_ett_exception(e):
        logger.error("ETT exception: %s", str(e))
        return jsonify(e.to_dict()), 500
    
    @app.errorhandler(404)
    def handle_not_found(e):
        logger.warning("404 error for path: %s", request.path)
        return jsonify({
            "error": "NOT_FOUND",
            "message": "The requested resource could not be found.",
            "path": request.path
        }), 404
    
    @app.errorhandler(405)
    def handle_method_not_allowed(e):
        logger.warning("405 error for %s %s", request.method, request.path)
        return jsonify({
            "error": "METHOD_NOT_ALLOWED",
            "message": f"Method {request.method} is not allowed for this endpoint.",
            "allowed_methods": e.valid_methods if hasattr(e, 'valid_methods') else []
        }), 405
    
    @app.errorhandler(413)
    def handle_payload_too_large(e):
        logger.warning("Payload too large: %s", request.content_length)
        return jsonify({
            "error": "PAYLOAD_TOO_LARGE",
            "message": "Request payload is too large.",
            "max_size": app.config.get('MAX_CONTENT_LENGTH', 'unknown')
        }), 413
    
    @app.errorhandler(415)
    def handle_unsupported_media_type(e):
        logger.warning("Unsupported media type: %s", request.content_type)
        return jsonify({
            "error": "UNSUPPORTED_MEDIA_TYPE",
            "message": "The media type of the request is not supported.",
            "content_type": request.content_type
        }), 415
    
    @app.errorhandler(500)
    def handle_internal_error(e):
        logger.error("Internal server error: %s", str(e), exc_info=True)
        return jsonify({
            "error": "INTERNAL_SERVER_ERROR",
            "message": "An unexpected error occurred. Please try again later.",
            "request_id": request.headers.get('X-Request-ID', '')
        }), 500
    
    @app.errorhandler(Exception)
    def handle_unexpected_error(e):
        logger.error("Unexpected error: %s", str(e), exc_info=True)
        return jsonify({
            "error": "UNEXPECTED_ERROR",
            "message": "An unexpected error occurred. Please contact support if this persists.",
            "request_id": request.headers.get('X-Request-ID', '')
        }), 500
