from __future__ import annotations

import base64
import hashlib
import hmac
import ipaddress
import json
import mimetypes
import re
import smtplib
import socket
import ssl
import time
from collections import defaultdict
from email.message import EmailMessage
from email.utils import formatdate, make_msgid
from pathlib import PurePath
from typing import Any
from urllib.parse import urlparse

import httpx
from email_validator import EmailNotValidError, validate_email

from ett_gns_app.channels.contracts import AdapterError, ChannelAdapter, SendResult

MAX_ATTACHMENT_BYTES = 10 * 1024 * 1024
MAX_RESPONSE_EXCERPT = 4096
E164 = re.compile(r"^\+[1-9]\d{7,14}$")
SAFE_ATTACHMENT_TYPES = {
    "application/pdf",
    "image/gif",
    "image/jpeg",
    "image/png",
    "text/csv",
    "text/plain",
}
METADATA_IPS = {
    ipaddress.ip_address("169.254.169.254"),
    ipaddress.ip_address("100.100.100.200"),
}


def normalize_http_error(response: httpx.Response) -> AdapterError:
    retryable = response.status_code == 429 or response.status_code >= 500
    code = "PROVIDER_RATE_LIMITED" if response.status_code == 429 else "PROVIDER_HTTP_ERROR"
    if response.status_code in {401, 403}:
        code = "PROVIDER_AUTH_FAILED"
        retryable = False
    return AdapterError(
        code,
        f"Provider returned HTTP {response.status_code}",
        retryable=retryable,
        provider_status=response.status_code,
    )


class FakeAdapter:
    def __init__(self, channel_name: str):
        self.channel_name = channel_name

    def validate_provider_config(
        self, public_config: dict[str, Any], secret: dict[str, Any]
    ) -> None:
        return None

    def validate_recipient(self, recipient: dict[str, Any]) -> None:
        if not recipient:
            raise AdapterError("INVALID_RECIPIENT", "Recipient is empty", retryable=False)

    def validate_content(self, content: dict[str, Any]) -> None:
        if not content:
            raise AdapterError("INVALID_CONTENT", "Content is empty", retryable=False)

    def send(
        self,
        public_config: dict[str, Any],
        secret: dict[str, Any],
        sender: dict[str, Any],
        recipient: dict[str, Any],
        content: dict[str, Any],
        metadata: dict[str, Any],
    ) -> SendResult:
        self.validate_recipient(recipient)
        self.validate_content(content)
        outcome = public_config.get("outcome", "accepted")
        if outcome == "temporary_failure":
            raise AdapterError("FAKE_TEMPORARY", "Deterministic temporary failure", retryable=True)
        if outcome == "permanent_failure":
            raise AdapterError("FAKE_PERMANENT", "Deterministic permanent failure", retryable=False)
        digest = hashlib.sha256(
            json.dumps(
                {"recipient": recipient, "content": content, "metadata": metadata},
                sort_keys=True,
            ).encode()
        ).hexdigest()[:24]
        return SendResult(accepted=True, provider_message_id=f"fake_{digest}")


class SMTPAdapter:
    channel_name = "email"

    def validate_provider_config(
        self, public_config: dict[str, Any], secret: dict[str, Any]
    ) -> None:
        required = {"host", "port", "security", "from_email"}
        missing = required - public_config.keys()
        if missing:
            raise AdapterError(
                "SMTP_CONFIG_INVALID", f"Missing SMTP fields: {sorted(missing)}", retryable=False
            )
        if public_config["security"] not in {"ssl", "starttls", "plain"}:
            raise AdapterError(
                "SMTP_CONFIG_INVALID", "Unsupported SMTP security mode", retryable=False
            )

    def validate_recipient(self, recipient: dict[str, Any]) -> None:
        try:
            validate_email(recipient.get("email", ""), check_deliverability=False)
        except EmailNotValidError as exc:
            raise AdapterError("INVALID_RECIPIENT", str(exc), retryable=False) from exc

    def validate_content(self, content: dict[str, Any]) -> None:
        if not content.get("subject") or not content.get("text"):
            raise AdapterError(
                "EMAIL_CONTENT_INVALID",
                "Email requires subject and text alternatives",
                retryable=False,
            )

    def _build_message(
        self,
        public_config: dict[str, Any],
        sender: dict[str, Any],
        recipient: dict[str, Any],
        content: dict[str, Any],
        metadata: dict[str, Any],
    ) -> EmailMessage:
        message = EmailMessage()
        from_email = sender.get("from_email") or public_config["from_email"]
        from_name = sender.get("from_name")
        message["From"] = f"{from_name} <{from_email}>" if from_name else from_email
        message["To"] = recipient["email"]
        message["Subject"] = content["subject"]
        message["Date"] = formatdate(localtime=False)
        message["Message-ID"] = make_msgid(domain=from_email.split("@")[-1])
        if sender.get("reply_to"):
            message["Reply-To"] = sender["reply_to"]
        if metadata.get("correlation_id"):
            message["X-GNS-Correlation-ID"] = str(metadata["correlation_id"])[:200]
        message.set_content(content["text"])
        if content.get("html"):
            message.add_alternative(content["html"], subtype="html")
        for attachment in content.get("attachments", []):
            filename = PurePath(str(attachment.get("filename", ""))).name
            if not filename or filename != attachment.get("filename"):
                raise AdapterError(
                    "ATTACHMENT_INVALID", "Attachment filename is unsafe", retryable=False
                )
            try:
                payload = base64.b64decode(attachment.get("content_base64", ""), validate=True)
            except ValueError as exc:
                raise AdapterError(
                    "ATTACHMENT_INVALID", "Attachment is not valid base64", retryable=False
                ) from exc
            if len(payload) > MAX_ATTACHMENT_BYTES:
                raise AdapterError(
                    "ATTACHMENT_TOO_LARGE", "Attachment exceeds 10 MB", retryable=False
                )
            content_type = attachment.get("content_type") or mimetypes.guess_type(filename)[0]
            if content_type not in SAFE_ATTACHMENT_TYPES:
                raise AdapterError(
                    "ATTACHMENT_TYPE_FORBIDDEN",
                    f"Attachment type {content_type!r} is forbidden",
                    retryable=False,
                )
            maintype, subtype = content_type.split("/", 1)
            message.add_attachment(payload, maintype=maintype, subtype=subtype, filename=filename)
        return message

    def send(
        self,
        public_config: dict[str, Any],
        secret: dict[str, Any],
        sender: dict[str, Any],
        recipient: dict[str, Any],
        content: dict[str, Any],
        metadata: dict[str, Any],
    ) -> SendResult:
        self.validate_provider_config(public_config, secret)
        self.validate_recipient(recipient)
        self.validate_content(content)
        message = self._build_message(public_config, sender, recipient, content, metadata)
        host = public_config["host"]
        port = int(public_config["port"])
        timeout = float(public_config.get("timeout_seconds", 10))
        security = public_config["security"]
        try:
            if security == "ssl":
                connection: smtplib.SMTP = smtplib.SMTP_SSL(
                    host, port, timeout=timeout, context=ssl.create_default_context()
                )
            else:
                connection = smtplib.SMTP(host, port, timeout=timeout)
            with connection as server:
                if security == "starttls":
                    server.starttls(context=ssl.create_default_context())
                username = public_config.get("username")
                password = secret.get("password")
                if username or password:
                    if not username or not password:
                        raise AdapterError(
                            "SMTP_CONFIG_INVALID",
                            "SMTP username and password must be configured together",
                            retryable=False,
                        )
                    server.login(username, password)
                refused = server.send_message(message)
                if refused:
                    raise AdapterError(
                        "SMTP_RECIPIENT_REFUSED",
                        "SMTP server refused one or more recipients",
                        retryable=False,
                    )
            return SendResult(
                accepted=True,
                provider_message_id=str(message["Message-ID"]),
                status="provider_accepted",
            )
        except AdapterError:
            raise
        except smtplib.SMTPAuthenticationError as exc:
            raise AdapterError("PROVIDER_AUTH_FAILED", str(exc), retryable=False) from exc
        except smtplib.SMTPRecipientsRefused as exc:
            raise AdapterError("SMTP_RECIPIENT_REFUSED", str(exc), retryable=False) from exc
        except smtplib.SMTPResponseException as exc:
            retryable = 400 <= exc.smtp_code < 500
            raise AdapterError(
                f"SMTP_{exc.smtp_code}", str(exc.smtp_error), retryable=retryable
            ) from exc
        except ssl.SSLCertVerificationError as exc:
            raise AdapterError(
                "SMTP_TLS_FAILED",
                "SMTP certificate verification failed. Install the full server certificate chain "
                "or use a certificate trusted by the runtime.",
                retryable=False,
            ) from exc
        except (TimeoutError, OSError, smtplib.SMTPServerDisconnected) as exc:
            raise AdapterError("SMTP_UNAVAILABLE", str(exc), retryable=True) from exc
        except smtplib.SMTPException as exc:
            raise AdapterError("SMTP_ERROR", str(exc), retryable=True) from exc

    def test_connection(self, public_config: dict[str, Any], secret: dict[str, Any]) -> None:
        self.validate_provider_config(public_config, secret)
        host = public_config["host"]
        port = int(public_config["port"])
        timeout = float(public_config.get("timeout_seconds", 10))
        security = public_config["security"]
        try:
            if security == "ssl":
                connection: smtplib.SMTP = smtplib.SMTP_SSL(
                    host, port, timeout=timeout, context=ssl.create_default_context()
                )
            else:
                connection = smtplib.SMTP(host, port, timeout=timeout)
            with connection as server:
                if security == "starttls":
                    server.starttls(context=ssl.create_default_context())
                if public_config.get("username"):
                    server.login(public_config["username"], secret["password"])
                server.noop()
        except smtplib.SMTPAuthenticationError as exc:
            raise AdapterError("PROVIDER_AUTH_FAILED", str(exc), retryable=False) from exc
        except ssl.SSLCertVerificationError as exc:
            raise AdapterError(
                "SMTP_TLS_FAILED",
                "SMTP certificate verification failed. Install the full server certificate chain "
                "or use a certificate trusted by the runtime.",
                retryable=False,
            ) from exc
        except (OSError, smtplib.SMTPException) as exc:
            raise AdapterError("SMTP_UNAVAILABLE", str(exc), retryable=True) from exc


def validate_public_destination(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise AdapterError(
            "WEBHOOK_URL_INVALID", "Webhook destination must be an HTTPS URL", retryable=False
        )
    if parsed.hostname.lower() == "localhost":
        raise AdapterError(
            "WEBHOOK_SSRF_BLOCKED", "Localhost destinations are forbidden", retryable=False
        )
    try:
        addresses = {
            ipaddress.ip_address(info[4][0])
            for info in socket.getaddrinfo(parsed.hostname, parsed.port or 443)
        }
    except socket.gaierror as exc:
        raise AdapterError("WEBHOOK_DNS_FAILED", str(exc), retryable=True) from exc
    for address in addresses:
        if (
            address.is_private
            or address.is_loopback
            or address.is_link_local
            or address.is_multicast
            or address.is_reserved
            or address.is_unspecified
            or address in METADATA_IPS
        ):
            raise AdapterError(
                "WEBHOOK_SSRF_BLOCKED",
                "Webhook resolved to a forbidden network",
                retryable=False,
            )


class WebhookAdapter:
    channel_name = "webhook"

    def __init__(self, transport: httpx.BaseTransport | None = None):
        self._transport = transport
        self._failures: dict[str, int] = defaultdict(int)
        self._open_until: dict[str, float] = {}

    def validate_provider_config(
        self, public_config: dict[str, Any], secret: dict[str, Any]
    ) -> None:
        validate_public_destination(public_config.get("url", ""))
        if not secret.get("signing_secret") and not secret.get("signing_secrets"):
            raise AdapterError(
                "WEBHOOK_SECRET_MISSING", "Webhook signing secret is required", retryable=False
            )

    def validate_recipient(self, recipient: dict[str, Any]) -> None:
        if recipient.get("url"):
            validate_public_destination(recipient["url"])

    def validate_content(self, content: dict[str, Any]) -> None:
        if "body" not in content:
            raise AdapterError(
                "WEBHOOK_CONTENT_INVALID", "Webhook body is required", retryable=False
            )

    def send(
        self,
        public_config: dict[str, Any],
        secret: dict[str, Any],
        sender: dict[str, Any],
        recipient: dict[str, Any],
        content: dict[str, Any],
        metadata: dict[str, Any],
    ) -> SendResult:
        self.validate_provider_config(public_config, secret)
        self.validate_recipient(recipient)
        self.validate_content(content)
        url = recipient.get("url") or public_config["url"]
        key = urlparse(url).netloc
        if self._open_until.get(key, 0) > time.monotonic():
            raise AdapterError("CIRCUIT_OPEN", "Webhook circuit is open", retryable=True)
        timestamp = str(int(time.time()))
        body = json.dumps(content["body"], sort_keys=True, separators=(",", ":")).encode()
        signing_value = secret.get("signing_secret") or secret["signing_secrets"][0]
        signing_secret = str(signing_value).encode()
        signature = hmac.new(
            signing_secret, timestamp.encode() + b"." + body, hashlib.sha256
        ).hexdigest()
        headers = {
            "Content-Type": "application/json",
            "X-GNS-Timestamp": timestamp,
            "X-GNS-Signature": f"v1={signature}",
            "User-Agent": "ETT-GNS/0.2",
        }
        try:
            with httpx.Client(
                timeout=float(public_config.get("timeout_seconds", 10)),
                follow_redirects=False,
                transport=self._transport,
            ) as client:
                response = client.post(url, content=body, headers=headers)
            if 300 <= response.status_code < 400:
                raise AdapterError(
                    "WEBHOOK_REDIRECT_BLOCKED", "Webhook redirects are disabled", retryable=False
                )
            if response.status_code >= 400:
                raise normalize_http_error(response)
            self._failures[key] = 0
            return SendResult(
                accepted=True,
                provider_message_id=response.headers.get("X-Request-ID"),
                response_excerpt=response.text[:MAX_RESPONSE_EXCERPT],
            )
        except AdapterError as exc:
            if exc.retryable:
                self._failures[key] += 1
                threshold = int(public_config.get("circuit_breaker_threshold", 5))
                if self._failures[key] >= threshold:
                    self._open_until[key] = time.monotonic() + float(
                        public_config.get("circuit_breaker_seconds", 30)
                    )
            raise
        except (httpx.TimeoutException, httpx.NetworkError) as exc:
            self._failures[key] += 1
            raise AdapterError("WEBHOOK_UNAVAILABLE", str(exc), retryable=True) from exc


class JSONAPIAdapter:
    """Shared normalized HTTP adapter for SMS, push, Telegram and WhatsApp."""

    def __init__(
        self,
        channel_name: str,
        transport: httpx.BaseTransport | None = None,
    ):
        self.channel_name = channel_name
        self._transport = transport

    def validate_provider_config(
        self, public_config: dict[str, Any], secret: dict[str, Any]
    ) -> None:
        if not public_config.get("base_url"):
            raise AdapterError("PROVIDER_CONFIG_INVALID", "base_url is required", retryable=False)

    def validate_recipient(self, recipient: dict[str, Any]) -> None:
        if self.channel_name in {"sms", "whatsapp"} and not E164.fullmatch(
            str(recipient.get("phone", ""))
        ):
            raise AdapterError("INVALID_RECIPIENT", "Phone number must be E.164", retryable=False)
        if self.channel_name == "push" and not recipient.get("token"):
            raise AdapterError("INVALID_RECIPIENT", "Push token is required", retryable=False)
        if self.channel_name == "telegram" and not recipient.get("chat_id"):
            raise AdapterError("INVALID_RECIPIENT", "Telegram chat_id is required", retryable=False)

    def validate_content(self, content: dict[str, Any]) -> None:
        if not content:
            raise AdapterError("INVALID_CONTENT", "Content is required", retryable=False)
        if self.channel_name == "whatsapp" and not content.get("opt_in_reference"):
            raise AdapterError(
                "WHATSAPP_OPT_IN_REQUIRED",
                "WhatsApp delivery requires opt-in reference metadata",
                retryable=False,
            )

    def _request(
        self,
        public_config: dict[str, Any],
        secret: dict[str, Any],
        recipient: dict[str, Any],
        content: dict[str, Any],
    ) -> tuple[str, dict[str, Any], dict[str, str]]:
        base = public_config["base_url"].rstrip("/")
        if self.channel_name == "sms":
            url = f"{base}/2010-04-01/Accounts/{public_config['account_sid']}/Messages.json"
            payload = {
                "To": recipient["phone"],
                "From": public_config["from_number"],
                "Body": content["text"],
            }
            auth = (public_config["account_sid"], secret["auth_token"])
            return url, payload, {"Authorization": httpx.BasicAuth(*auth)._auth_header}
        if self.channel_name == "telegram":
            media = content.get("media")
            method = "sendMessage"
            telegram_payload: dict[str, Any] = {"chat_id": recipient["chat_id"]}
            if media and media.get("type") in {"photo", "document"}:
                method = "sendPhoto" if media["type"] == "photo" else "sendDocument"
                telegram_payload[media["type"]] = media["url"]
                telegram_payload["caption"] = content.get("body")
            else:
                telegram_payload["text"] = content["body"]
            telegram_payload["parse_mode"] = content.get("parse_mode")
            telegram_payload["reply_markup"] = {
                "inline_keyboard": content.get("inline_keyboard", [])
            }
            url = f"{base}/bot{secret['bot_token']}/{method}"
            return url, telegram_payload, {}
        if self.channel_name == "whatsapp":
            url = (
                f"{base}/{public_config['api_version']}/{public_config['phone_number_id']}/messages"
            )
            components = list(content.get("parameters", []))
            media_header = content.get("media_header")
            if media_header:
                media_type = media_header["type"]
                components.insert(
                    0,
                    {
                        "type": "header",
                        "parameters": [
                            {
                                "type": media_type,
                                media_type: {"link": media_header["url"]},
                            }
                        ],
                    },
                )
            payload = {
                "messaging_product": "whatsapp",
                "to": recipient["phone"],
                "type": "template",
                "template": {
                    "name": content["template_name"],
                    "language": {"code": content["language"]},
                    "components": components,
                },
            }
            return url, payload, {"Authorization": f"Bearer {secret['access_token']}"}
        url = f"{base}/v1/projects/{public_config['project_id']}/messages:send"
        payload = {
            "message": {
                "token": recipient["token"],
                "notification": {
                    "title": content["title"],
                    "body": content["body"],
                    **({"image": content["image"]} if content.get("image") else {}),
                },
                "data": {
                    **content.get("data", {}),
                    **({"deep_link": content["deep_link"]} if content.get("deep_link") else {}),
                },
                "android": {
                    "ttl": content.get("ttl", "3600s"),
                    **(
                        {"collapse_key": content["collapse_key"]}
                        if content.get("collapse_key")
                        else {}
                    ),
                },
            }
        }
        return url, payload, {"Authorization": f"Bearer {secret['access_token']}"}

    def send(
        self,
        public_config: dict[str, Any],
        secret: dict[str, Any],
        sender: dict[str, Any],
        recipient: dict[str, Any],
        content: dict[str, Any],
        metadata: dict[str, Any],
    ) -> SendResult:
        self.validate_provider_config(public_config, secret)
        self.validate_recipient(recipient)
        self.validate_content(content)
        url, payload, headers = self._request(public_config, secret, recipient, content)
        try:
            with httpx.Client(
                timeout=float(public_config.get("timeout_seconds", 10)),
                follow_redirects=False,
                transport=self._transport,
            ) as client:
                response = client.post(url, json=payload, headers=headers)
            if response.status_code >= 400:
                raise normalize_http_error(response)
            response_data = response.json()
            message_id = (
                response_data.get("sid")
                or response_data.get("name")
                or response_data.get("result", {}).get("message_id")
                or (response_data.get("messages") or [{}])[0].get("id")
            )
            return SendResult(
                accepted=True,
                provider_message_id=message_id,
                response_excerpt=response.text[:MAX_RESPONSE_EXCERPT],
            )
        except AdapterError:
            raise
        except (httpx.TimeoutException, httpx.NetworkError) as exc:
            raise AdapterError("PROVIDER_UNAVAILABLE", str(exc), retryable=True) from exc


def adapter_for(
    channel: str,
    provider_type: str,
    *,
    transport: httpx.BaseTransport | None = None,
) -> ChannelAdapter:
    if provider_type == "fake":
        return FakeAdapter(channel)
    if channel == "email" and provider_type == "smtp":
        return SMTPAdapter()
    if channel == "webhook" and provider_type == "http":
        return WebhookAdapter(transport=transport)
    expected = {
        "sms": "twilio",
        "push": "fcm",
        "telegram": "telegram_bot",
        "whatsapp": "meta_cloud",
    }
    if expected.get(channel) == provider_type:
        return JSONAPIAdapter(channel, transport=transport)
    raise AdapterError(
        "ADAPTER_UNSUPPORTED",
        f"No adapter for channel={channel!r}, provider_type={provider_type!r}",
        retryable=False,
    )
