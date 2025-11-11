"""
ETT GNS API Routes with enhanced security and validation.
"""
from flask import Blueprint, request, jsonify, g
import time
from ett_gns_app.gns_controller import GnsController
from ett_gns_app.core.validation import RequestValidator
from ett_gns_app.core.security import rate_limit, validate_content_type, security_manager
from ett_gns_app.core.config import get_config
from ett_gns_app.utils.helpers.logger import setup_logger, log_request, log_response


# Initialize logger and controller
logger = setup_logger(__name__)
gns_controller = GnsController()

# Create Blueprint
api_bp = Blueprint('api', __name__, url_prefix='/api/v1')
main_bp = Blueprint('main', __name__)


@main_bp.route("/", methods=["GET"])
def home():
    """
    Home endpoint with service information.
    """
    config = get_config()
    
    return jsonify({
        "service": "ETT GNS (Email Template Transmission - Generic Notification Service)",
        "version": "v2.0.0",
        "status": "operational",
        "environment": config.environment,
        "documentation": "/api/v1/docs",
        "health": "/health",
        "endpoints": {
            "send_notification": "/api/v1/send_notification",
            "health": "/health",
            "metrics": "/metrics"
        }
    }), 200


@main_bp.route("/health", methods=["GET"])
def health_check():
    """
    Comprehensive health check endpoint.
    """
    start_time = time.time()
    health_status = {
        "status": "healthy",
        "timestamp": time.time(),
        "version": "v2.0.0",
        "checks": {}
    }
    
    try:
        config = get_config()
        
        # Check configuration
        health_status["checks"]["configuration"] = {
            "status": "healthy",
            "environment": config.environment
        }
        
        # Check SMTP configuration
        if config.smtp:
            health_status["checks"]["smtp"] = {
                "status": "healthy",
                "server": config.smtp.server,
                "port": config.smtp.port
            }
        else:
            health_status["checks"]["smtp"] = {
                "status": "unhealthy",
                "error": "SMTP configuration missing"
            }
            health_status["status"] = "degraded"
        
        # Check Redis connection (for rate limiting)
        try:
            redis_client = security_manager.rate_limiter.redis_client
            if redis_client:
                redis_client.ping()
                health_status["checks"]["redis"] = {"status": "healthy"}
            else:
                health_status["checks"]["redis"] = {
                    "status": "degraded",
                    "message": "Using in-memory rate limiting"
                }
        except Exception as e:
            health_status["checks"]["redis"] = {
                "status": "unhealthy",
                "error": str(e)
            }
            health_status["status"] = "degraded"
        
        # Check template directory
        try:
            import os
            if os.path.exists(config.template_dir):
                health_status["checks"]["templates"] = {"status": "healthy"}
            else:
                health_status["checks"]["templates"] = {
                    "status": "unhealthy",
                    "error": f"Template directory not found: {config.template_dir}"
                }
                health_status["status"] = "unhealthy"
        except Exception as e:
            health_status["checks"]["templates"] = {
                "status": "unhealthy",
                "error": str(e)
            }
            health_status["status"] = "unhealthy"
        
    except Exception as e:
        logger.error("Health check failed: %s", str(e))
        health_status = {
            "status": "unhealthy",
            "timestamp": time.time(),
            "error": str(e)
        }
    
    # Calculate response time
    health_status["response_time_ms"] = round((time.time() - start_time) * 1000, 2)
    
    status_code = 200 if health_status["status"] == "healthy" else (503 if health_status["status"] == "unhealthy" else 200)
    
    return jsonify(health_status), status_code


@api_bp.route("/send_notification", methods=["POST"])
@validate_content_type(["application/json"])
@rate_limit(requests_per_minute=60, requests_per_hour=1000)
def send_notification():
    """
    Send notification through specified channel with enhanced validation and security.
    """
    start_time = time.time()
    
    try:
        # Get and validate JSON payload
        if not request.is_json:
            return jsonify({
                "error": "INVALID_REQUEST",
                "message": "Request must be JSON"
            }), 400
        
        payload = request.get_json()
        if not payload:
            return jsonify({
                "error": "EMPTY_PAYLOAD",
                "message": "Request payload cannot be empty"
            }), 400
        
        # Validate payload size
        RequestValidator.validate_payload_size(request.get_data())
        
        # Validate request structure and data
        validated_data = RequestValidator.validate_send_notification(payload)
        
        # Sanitize template data
        if validated_data.get("data"):
            validated_data["data"] = RequestValidator.sanitize_template_data(
                validated_data["data"]
            )
        
        # Log the request
        logger.info(
            "Processing notification request",
            extra={
                "channel": validated_data["channel_name"],
                "recipient": validated_data["recipient"],
                "template": validated_data["template_name"],
                "event_type": "notification_request"
            }
        )
        
        # Send notification
        gns_controller.send_notification(
            channel_name=validated_data["channel_name"],
            recipient=validated_data["recipient"],
            subject=validated_data["subject"],
            template_name=validated_data["template_name"],
            data=validated_data.get("data", {})
        )
        
        # Calculate processing time
        processing_time = round((time.time() - start_time) * 1000, 2)
        
        # Log success
        logger.info(
            "Notification sent successfully",
            extra={
                "channel": validated_data["channel_name"],
                "recipient": validated_data["recipient"],
                "template": validated_data["template_name"],
                "processing_time_ms": processing_time,
                "event_type": "notification_success"
            }
        )
        
        response_data = {
            "message": "Notification sent successfully",
            "request_id": g.get('correlation_id', ''),
            "processing_time_ms": processing_time,
            "channel": validated_data["channel_name"],
            "template": validated_data["template_name"]
        }
        
        return jsonify(response_data), 200
        
    except Exception as e:
        # This will be caught by the global error handlers
        raise


@api_bp.route("/templates", methods=["GET"])
@rate_limit(requests_per_minute=30)
def list_templates():
    """
    List available email templates.
    """
    try:
        from ett_gns_app.gns_constant import AllTemplatesData
        
        templates_data = AllTemplatesData()
        templates_info = []
        
        for template_name, required_vars in templates_data.TEMPLATES.items():
            templates_info.append({
                "name": template_name,
                "required_variables": required_vars,
                "description": f"Template requiring: {', '.join(required_vars)}"
            })
        
        return jsonify({
            "templates": templates_info,
            "total_count": len(templates_info)
        }), 200
        
    except Exception as e:
        logger.error("Failed to list templates: %s", str(e))
        raise


@api_bp.route("/docs", methods=["GET"])
def api_documentation():
    """
    API documentation endpoint.
    """
    docs = {
        "service": "ETT GNS API",
        "version": "v2.0.0",
        "description": "Generic Notification Service for sending templated emails",
        "base_url": request.host_url.rstrip('/') + "/api/v1",
        "authentication": {
            "type": "API Key",
            "header": "X-API-Key",
            "description": "Include your API key in the X-API-Key header"
        },
        "rate_limits": {
            "send_notification": "60 requests per minute, 1000 per hour",
            "other_endpoints": "30 requests per minute"
        },
        "endpoints": {
            "POST /send_notification": {
                "description": "Send a notification via email",
                "required_fields": {
                    "channel_name": "Notification channel (currently only 'email')",
                    "recipient": "Valid email address",
                    "subject": "Email subject (1-998 characters)",
                    "template_name": "Template file name (must end with .html)"
                },
                "optional_fields": {
                    "data": "Dictionary of template variables"
                },
                "example": {
                    "channel_name": "email",
                    "recipient": "user@example.com",
                    "subject": "Welcome to our service!",
                    "template_name": "welcome_email.html",
                    "data": {
                        "user_name": "John Doe",
                        "welcome_message": "Thank you for joining us!"
                    }
                }
            },
            "GET /templates": {
                "description": "List available email templates",
                "response": "Array of template objects with required variables"
            },
            "GET /health": {
                "description": "Service health check",
                "response": "Health status and system checks"
            }
        },
        "error_codes": {
            "VALIDATION_ERROR": "Request validation failed",
            "RATE_LIMIT_EXCEEDED": "Too many requests",
            "TEMPLATE_NOT_FOUND": "Specified template doesn't exist",
            "EMAIL_DELIVERY_ERROR": "Failed to send email",
            "INTERNAL_SERVER_ERROR": "Unexpected server error"
        }
    }
    
    return jsonify(docs), 200


@api_bp.route("/metrics", methods=["GET"])
@rate_limit(requests_per_minute=10)
def metrics():
    """
    Basic metrics endpoint.
    """
    # In a production environment, you would use proper metrics collection
    # like Prometheus metrics
    basic_metrics = {
        "service": "ett_gns",
        "version": "v2.0.0",
        "uptime_seconds": time.time() - g.get('start_time', time.time()),
        "timestamp": time.time(),
        "note": "Detailed metrics available via /metrics endpoint with Prometheus format"
    }
    
    return jsonify(basic_metrics), 200


def register_blueprints(app):
    """Register all application blueprints."""
    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp)
    
    logger.info("Blueprints registered successfully")
