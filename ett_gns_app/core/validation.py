"""
Request validation schemas and middleware.
"""
import re
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass
from ett_gns_app.core.exceptions import ValidationError, PayloadTooLargeError


@dataclass
class ValidationRule:
    """Validation rule for a field."""
    required: bool = False
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    pattern: Optional[str] = None
    allowed_values: Optional[List[str]] = None
    field_type: type = str


class RequestValidator:
    """Request validation utility."""
    
    # Email validation regex
    EMAIL_PATTERN = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    
    # Notification request schema
    SEND_NOTIFICATION_SCHEMA = {
        "channel_name": ValidationRule(
            required=True,
            allowed_values=["email"],  # Can be extended for SMS, WhatsApp, etc.
            max_length=50
        ),
        "recipient": ValidationRule(
            required=True,
            pattern=EMAIL_PATTERN,
            max_length=320  # RFC 5321 limit
        ),
        "subject": ValidationRule(
            required=True,
            min_length=1,
            max_length=998  # RFC 2822 limit
        ),
        "template_name": ValidationRule(
            required=True,
            pattern=r'^[a-zA-Z0-9_-]+\.html$',
            max_length=255
        ),
        "data": ValidationRule(
            required=False,
            field_type=dict
        )
    }
    
    @classmethod
    def validate_send_notification(cls, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Validate send notification request payload."""
        return cls._validate_payload(payload, cls.SEND_NOTIFICATION_SCHEMA)
    
    @classmethod
    def _validate_payload(
        cls, 
        payload: Dict[str, Any], 
        schema: Dict[str, ValidationRule]
    ) -> Dict[str, Any]:
        """Validate payload against schema."""
        if not isinstance(payload, dict):
            raise ValidationError("Request payload must be a JSON object")
        
        validated_data = {}
        errors = []
        
        # Check for required fields and validate each field
        for field_name, rule in schema.items():
            value = payload.get(field_name)
            
            # Check if required field is missing
            if rule.required and (value is None or value == ""):
                errors.append(f"Field '{field_name}' is required")
                continue
            
            # Skip validation for optional fields that are not provided
            if value is None and not rule.required:
                validated_data[field_name] = None
                continue
            
            # Type validation
            if not isinstance(value, rule.field_type):
                errors.append(
                    f"Field '{field_name}' must be of type {rule.field_type.__name__}"
                )
                continue
            
            # String-specific validations
            if rule.field_type == str and value is not None:
                # Length validation
                if rule.min_length is not None and len(value) < rule.min_length:
                    errors.append(
                        f"Field '{field_name}' must be at least {rule.min_length} characters long"
                    )
                
                if rule.max_length is not None and len(value) > rule.max_length:
                    errors.append(
                        f"Field '{field_name}' must be at most {rule.max_length} characters long"
                    )
                
                # Pattern validation
                if rule.pattern and not re.match(rule.pattern, value):
                    if field_name == "recipient":
                        errors.append(f"Field '{field_name}' must be a valid email address")
                    elif field_name == "template_name":
                        errors.append(f"Field '{field_name}' must be a valid HTML template name")
                    else:
                        errors.append(f"Field '{field_name}' format is invalid")
                
                # Allowed values validation
                if rule.allowed_values and value not in rule.allowed_values:
                    errors.append(
                        f"Field '{field_name}' must be one of: {', '.join(rule.allowed_values)}"
                    )
            
            validated_data[field_name] = value
        
        # Check for unexpected fields
        unexpected_fields = set(payload.keys()) - set(schema.keys())
        if unexpected_fields:
            errors.append(f"Unexpected fields: {', '.join(unexpected_fields)}")
        
        if errors:
            raise ValidationError(
                "Validation failed",
                error_code="VALIDATION_ERROR",
                details={"errors": errors}
            )
        
        return validated_data
    
    @classmethod
    def sanitize_template_data(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize template data to prevent XSS attacks."""
        if not isinstance(data, dict):
            return {}
        
        sanitized = {}
        for key, value in data.items():
            if isinstance(value, str):
                # Basic HTML sanitization - escape dangerous characters
                sanitized[key] = (
                    value.replace("&", "&amp;")
                    .replace("<", "&lt;")
                    .replace(">", "&gt;")
                    .replace('"', "&quot;")
                    .replace("'", "&#x27;")
                    .replace("/", "&#x2F;")
                )
            elif isinstance(value, (int, float, bool)):
                sanitized[key] = value
            elif isinstance(value, dict):
                sanitized[key] = cls.sanitize_template_data(value)
            elif isinstance(value, list):
                sanitized[key] = [
                    cls.sanitize_template_data(item) if isinstance(item, dict)
                    else str(item).replace("<", "&lt;").replace(">", "&gt;")
                    for item in value
                ]
            else:
                # Convert other types to string and sanitize
                sanitized[key] = str(value).replace("<", "&lt;").replace(">", "&gt;")
        
        return sanitized
    
    @classmethod
    def validate_payload_size(cls, payload: Union[str, bytes], max_size: int = 1024 * 1024):
        """Validate payload size."""
        if isinstance(payload, str):
            size = len(payload.encode('utf-8'))
        else:
            size = len(payload)
        
        if size > max_size:
            raise PayloadTooLargeError(
                f"Payload size ({size} bytes) exceeds maximum allowed size ({max_size} bytes)",
                details={"payload_size": size, "max_size": max_size}
            )