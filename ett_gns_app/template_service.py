from __future__ import annotations

import re
from typing import Any

import bleach
from jinja2 import StrictUndefined, meta
from jinja2.exceptions import SecurityError, TemplateError
from jinja2.sandbox import SandboxedEnvironment
from jsonschema import Draft202012Validator

ALLOWED_HTML_TAGS = {
    "a",
    "b",
    "blockquote",
    "br",
    "code",
    "div",
    "em",
    "h1",
    "h2",
    "h3",
    "hr",
    "img",
    "li",
    "ol",
    "p",
    "pre",
    "span",
    "strong",
    "table",
    "tbody",
    "td",
    "th",
    "thead",
    "tr",
    "ul",
}
ALLOWED_HTML_ATTRIBUTES = {
    "a": ["href", "title"],
    "img": ["src", "alt", "title", "width", "height"],
    "td": ["colspan", "rowspan"],
    "th": ["colspan", "rowspan", "scope"],
    "*": ["class", "aria-label"],
}
ALLOWED_PROTOCOLS = {"https", "mailto"}
DANGEROUS_TEMPLATE_PATTERN = re.compile(
    r"(__|import|from_pyfile|cycler|joiner|namespace|lipsum|config|request|self)",
    re.IGNORECASE,
)


def environment() -> SandboxedEnvironment:
    env = SandboxedEnvironment(
        autoescape=True,
        undefined=StrictUndefined,
        enable_async=False,
    )
    env.filters = {
        "default": env.filters["default"],
        "escape": env.filters["escape"],
        "e": env.filters["e"],
        "lower": env.filters["lower"],
        "upper": env.filters["upper"],
        "title": env.filters["title"],
        "trim": env.filters["trim"],
        "replace": env.filters["replace"],
        "length": env.filters["length"],
    }
    env.globals.clear()
    return env


def required_content_fields(channel: str) -> set[str]:
    return {
        "email": {"subject", "html", "text"},
        "sms": {"text"},
        "webhook": {"body"},
        "push": {"title", "body"},
        "telegram": {"body"},
        "whatsapp": {
            "template_name",
            "language",
            "parameters",
            "opt_in_reference",
        },
        "in_app": {"title", "message"},
    }[channel]


def template_variables(source: str) -> set[str]:
    env = environment()
    parsed = env.parse(source)
    return set(meta.find_undeclared_variables(parsed))


def validate_template_content(
    channel: str,
    content: dict[str, Any],
    event_schema: dict[str, Any],
    sample_data: dict[str, Any],
) -> list[str]:
    errors: list[str] = []
    missing_fields = required_content_fields(channel) - content.keys()
    if missing_fields:
        errors.append(f"Missing channel content fields: {sorted(missing_fields)}")
    schema_properties = set(event_schema.get("properties", {}).keys())
    for field, value in content.items():
        if isinstance(value, str):
            if len(value.encode()) > 512_000:
                errors.append(f"Field {field!r} exceeds the 512 KB limit")
                continue
            if DANGEROUS_TEMPLATE_PATTERN.search(value):
                errors.append(f"Field {field!r} contains a forbidden template construct")
                continue
            try:
                undeclared = template_variables(value)
                unknown = undeclared - schema_properties
                if unknown:
                    errors.append(f"Field {field!r} uses undeclared variables: {sorted(unknown)}")
                environment().from_string(value).render(sample_data)
            except (TemplateError, SecurityError) as exc:
                errors.append(f"Field {field!r} is invalid: {exc}")
    validation_errors = sorted(
        error.message for error in Draft202012Validator(event_schema).iter_errors(sample_data)
    )
    errors.extend(f"Sample data: {message}" for message in validation_errors)
    if channel == "email" and isinstance(content.get("html"), str):
        html = content["html"]
        sanitized = bleach.clean(
            html,
            tags=ALLOWED_HTML_TAGS,
            attributes=ALLOWED_HTML_ATTRIBUTES,
            protocols=ALLOWED_PROTOCOLS,
            strip=True,
        )
        if sanitized != html:
            errors.append("HTML contains disallowed elements, attributes, or URL protocols")
    if channel == "in_app":
        severity = content.get("severity", "info")
        if severity not in {"info", "success", "warning", "error", "critical"}:
            errors.append("In-app severity must be info, success, warning, error, or critical")
        action = content.get("action")
        if action is not None:
            if not isinstance(action, dict):
                errors.append("In-app action must be an object")
            else:
                url = str(action.get("url", ""))
                action_type = action.get("type", "deep_link")
                if action_type not in {"deep_link"}:
                    errors.append("In-app action type must be deep_link")
                if not url.startswith("/") or url.startswith("//") or "javascript:" in url.lower():
                    errors.append("In-app action URL must be a safe relative path")
        toast = content.get("toast", {})
        if toast and not isinstance(toast, dict):
            errors.append("In-app toast must be an object")
        elif toast:
            auto_dismiss = toast.get("auto_dismiss_ms", 6000)
            if not isinstance(auto_dismiss, int) or not 1000 <= auto_dismiss <= 60000:
                errors.append("In-app toast auto_dismiss_ms must be between 1000 and 60000")
    return errors


def render_content(content: dict[str, Any], data: dict[str, Any]) -> dict[str, Any]:
    rendered: dict[str, Any] = {}
    env = environment()
    for field, value in content.items():
        if isinstance(value, str):
            result = env.from_string(value).render(data)
            rendered[field] = result
        elif isinstance(value, dict):
            rendered[field] = render_content(value, data)
        else:
            rendered[field] = value
    return rendered
