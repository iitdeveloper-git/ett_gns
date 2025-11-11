"""
Security middleware and utilities for the ETT GNS application.
"""
import time
import hashlib
from typing import Dict, Any, Optional
from functools import wraps
from flask import request, jsonify, g
import redis
from ett_gns_app.core.config import get_config
from ett_gns_app.core.exceptions import RateLimitExceededError, AuthenticationError
from ett_gns_app.utils.helpers.logger import setup_logger, set_correlation_id


logger = setup_logger(__name__)


class RateLimiter:
    """Redis-backed rate limiter."""
    
    def __init__(self, redis_client=None):
        self.redis_client = redis_client or self._get_redis_client()
    
    def _get_redis_client(self):
        """Get Redis client instance."""
        try:
            config = get_config()
            return redis.Redis(
                host='redis',  # Docker service name
                port=6379,
                password='ettredispass',  # Should be from config
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True
            )
        except Exception as e:
            logger.warning("Redis connection failed, using in-memory rate limiting: %s", e)
            return None
    
    def is_allowed(self, key: str, limit: int, window: int) -> tuple[bool, Dict[str, Any]]:
        """
        Check if request is allowed based on rate limit.
        
        Args:
            key: Rate limit key (e.g., IP address)
            limit: Maximum requests allowed
            window: Time window in seconds
            
        Returns:
            Tuple of (is_allowed, metadata)
        """
        if not self.redis_client:
            # Fallback to allowing all requests if Redis is unavailable
            logger.warning("Rate limiting unavailable - allowing request")
            return True, {"remaining": limit, "reset_time": time.time() + window}
        
        try:
            current_time = int(time.time())
            window_start = current_time - window
            
            # Use Redis sorted set for sliding window
            pipe = self.redis_client.pipeline()
            
            # Remove old entries
            pipe.zremrangebyscore(key, 0, window_start)
            
            # Count current requests
            pipe.zcard(key)
            
            # Add current request
            pipe.zadd(key, {str(current_time): current_time})
            
            # Set expiry
            pipe.expire(key, window)
            
            results = pipe.execute()
            current_count = results[1] + 1  # +1 for the request we just added
            
            is_allowed = current_count <= limit
            
            metadata = {
                "limit": limit,
                "remaining": max(0, limit - current_count),
                "reset_time": current_time + window,
                "retry_after": window if not is_allowed else 0
            }
            
            return is_allowed, metadata
            
        except Exception as e:
            logger.error("Rate limiting error: %s", e)
            # Allow request on error to avoid blocking legitimate traffic
            return True, {"remaining": limit, "reset_time": time.time() + window}


class SecurityManager:
    """Centralized security management."""
    
    def __init__(self):
        self.rate_limiter = RateLimiter()
        self.config = get_config()
    
    def get_client_ip(self, request) -> str:
        """Get client IP address from request."""
        # Check for forwarded headers (behind reverse proxy)
        forwarded_ips = request.headers.get('X-Forwarded-For')
        if forwarded_ips:
            return forwarded_ips.split(',')[0].strip()
        
        real_ip = request.headers.get('X-Real-IP')
        if real_ip:
            return real_ip
        
        return request.remote_addr or 'unknown'
    
    def generate_request_signature(self, payload: str, timestamp: str, secret: str) -> str:
        """Generate request signature for webhook validation."""
        message = f"{timestamp}.{payload}"
        signature = hashlib.sha256((secret + message).encode()).hexdigest()
        return f"sha256={signature}"
    
    def validate_request_signature(
        self, 
        payload: str, 
        timestamp: str, 
        received_signature: str, 
        secret: str,
        tolerance: int = 300
    ) -> bool:
        """Validate request signature to prevent tampering."""
        try:
            # Check timestamp tolerance (5 minutes by default)
            current_time = int(time.time())
            if abs(current_time - int(timestamp)) > tolerance:
                logger.warning("Request timestamp outside tolerance window")
                return False
            
            expected_signature = self.generate_request_signature(payload, timestamp, secret)
            
            # Constant-time comparison to prevent timing attacks
            return hashlib.sha256(expected_signature.encode()).hexdigest() == \
                   hashlib.sha256(received_signature.encode()).hexdigest()
                   
        except Exception as e:
            logger.error("Signature validation error: %s", e)
            return False


# Global security manager instance
security_manager = SecurityManager()


def require_api_key(f):
    """Decorator to require API key authentication."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')
        
        if not api_key:
            logger.warning("Missing API key in request")
            raise AuthenticationError("API key required")
        
        # In production, validate against database or secure storage
        # For now, check against environment variable
        expected_key = security_manager.config.secret_key  # This should be a separate API key
        
        if not hashlib.sha256(api_key.encode()).hexdigest() == \
               hashlib.sha256(expected_key.encode()).hexdigest():
            logger.warning("Invalid API key provided")
            raise AuthenticationError("Invalid API key")
        
        return f(*args, **kwargs)
    
    return decorated_function


def rate_limit(requests_per_minute: int = None, requests_per_hour: int = None):
    """Decorator for rate limiting endpoints."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            client_ip = security_manager.get_client_ip(request)
            
            # Check per-minute limit
            if requests_per_minute:
                minute_key = f"rate_limit:minute:{client_ip}"
                allowed, metadata = security_manager.rate_limiter.is_allowed(
                    minute_key, requests_per_minute, 60
                )
                
                if not allowed:
                    logger.warning(
                        "Rate limit exceeded for IP %s (per minute)", 
                        client_ip,
                        extra={"client_ip": client_ip, "limit_type": "minute"}
                    )
                    raise RateLimitExceededError(
                        "Rate limit exceeded",
                        details=metadata
                    )
            
            # Check per-hour limit
            if requests_per_hour:
                hour_key = f"rate_limit:hour:{client_ip}"
                allowed, metadata = security_manager.rate_limiter.is_allowed(
                    hour_key, requests_per_hour, 3600
                )
                
                if not allowed:
                    logger.warning(
                        "Rate limit exceeded for IP %s (per hour)", 
                        client_ip,
                        extra={"client_ip": client_ip, "limit_type": "hour"}
                    )
                    raise RateLimitExceededError(
                        "Rate limit exceeded",
                        details=metadata
                    )
            
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator


def request_logging_middleware():
    """Middleware for request logging and correlation ID generation."""
    def before_request():
        # Generate correlation ID for request tracking
        correlation_id = set_correlation_id()
        g.correlation_id = correlation_id
        g.start_time = time.time()
        
        # Log request
        logger.info(
            "Incoming request",
            extra={
                "method": request.method,
                "path": request.path,
                "client_ip": security_manager.get_client_ip(request),
                "user_agent": request.headers.get("User-Agent", ""),
                "content_length": request.content_length or 0,
                "event_type": "request_start"
            }
        )
    
    def after_request(response):
        # Calculate request duration
        duration = (time.time() - g.get('start_time', time.time())) * 1000
        
        # Log response
        logger.info(
            "Request completed",
            extra={
                "method": request.method,
                "path": request.path,
                "status_code": response.status_code,
                "duration_ms": round(duration, 2),
                "response_size": len(response.get_data()),
                "event_type": "request_end"
            }
        )
        
        # Add security headers
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response.headers['X-Request-ID'] = g.get('correlation_id', '')
        
        # Add rate limit headers if available
        if hasattr(g, 'rate_limit_remaining'):
            response.headers['X-RateLimit-Remaining'] = str(g.rate_limit_remaining)
            response.headers['X-RateLimit-Reset'] = str(g.rate_limit_reset)
        
        return response
    
    return before_request, after_request


def sanitize_filename(filename: str) -> str:
    """Sanitize filename to prevent directory traversal attacks."""
    import os
    import re
    
    # Remove directory separators and special characters
    sanitized = re.sub(r'[^\w\-_\.]', '', filename)
    
    # Prevent directory traversal
    sanitized = os.path.basename(sanitized)
    
    # Limit length
    if len(sanitized) > 255:
        name, ext = os.path.splitext(sanitized)
        sanitized = name[:255-len(ext)] + ext
    
    return sanitized


def validate_content_type(allowed_types: list):
    """Decorator to validate request content type."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            content_type = request.content_type
            
            if content_type not in allowed_types:
                logger.warning(
                    "Invalid content type: %s", content_type,
                    extra={"allowed_types": allowed_types}
                )
                return jsonify({
                    "error": "INVALID_CONTENT_TYPE",
                    "message": f"Content-Type must be one of: {', '.join(allowed_types)}"
                }), 415
            
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator