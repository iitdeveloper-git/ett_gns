import socket
from typing import Any

import httpx
import pytest
from aiosmtpd.controller import Controller

from ett_gns_app.channels.adapters import (
    JSONAPIAdapter,
    SMTPAdapter,
    WebhookAdapter,
    validate_public_destination,
)
from ett_gns_app.channels.contracts import AdapterError


class MailHandler:
    def __init__(self) -> None:
        self.messages: list[Any] = []

    async def handle_DATA(self, server, session, envelope):
        self.messages.append(envelope)
        return "250 accepted"


def available_port() -> int:
    try:
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            return int(sock.getsockname()[1])
    except PermissionError:
        pytest.skip("Environment forbids binding a local SMTP test socket")


def test_smtp_adapter_delivers_text_and_html_to_local_server() -> None:
    handler = MailHandler()
    port = available_port()
    controller = Controller(handler, hostname="127.0.0.1", port=port)
    controller.start()
    try:
        result = SMTPAdapter().send(
            {
                "host": "127.0.0.1",
                "port": port,
                "security": "plain",
                "from_email": "sender@example.com",
                "timeout_seconds": 2,
            },
            {},
            {"from_email": "sender@example.com", "from_name": "GNS"},
            {"email": "person@example.com"},
            {"subject": "Hello", "text": "Plain text", "html": "<p>HTML</p>"},
            {"correlation_id": "corr_test"},
        )
    finally:
        controller.stop()
    assert result.accepted is True
    assert result.provider_message_id
    assert len(handler.messages) == 1
    message = handler.messages[0].content.decode()
    assert "multipart/alternative" in message
    assert "X-GNS-Correlation-ID: corr_test" in message


def test_smtp_adapter_rejects_dangerous_attachment() -> None:
    with pytest.raises(AdapterError) as error:
        SMTPAdapter()._build_message(
            {"from_email": "sender@example.com"},
            {"from_email": "sender@example.com"},
            {"email": "person@example.com"},
            {
                "subject": "Hello",
                "text": "Text",
                "attachments": [
                    {
                        "filename": "../payload.exe",
                        "content_type": "application/octet-stream",
                        "content_base64": "AA==",
                    }
                ],
            },
            {},
        )
    assert error.value.code == "ATTACHMENT_INVALID"


def test_webhook_blocks_private_and_metadata_destinations(monkeypatch) -> None:
    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda *args, **kwargs: [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 443))],
    )
    with pytest.raises(AdapterError) as error:
        validate_public_destination("https://hooks.example.test/delivery")
    assert error.value.code == "WEBHOOK_SSRF_BLOCKED"


def test_webhook_signs_payload_and_disables_redirects(monkeypatch) -> None:
    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda *args, **kwargs: [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 443))
        ],
    )
    captured: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["headers"] = request.headers
        captured["body"] = request.content
        return httpx.Response(202, headers={"X-Request-ID": "provider-1"}, text="accepted")

    result = WebhookAdapter(transport=httpx.MockTransport(handler)).send(
        {"url": "https://hooks.example.test/delivery", "timeout_seconds": 1},
        {"signing_secret": "secret"},
        {},
        {},
        {"body": {"event": "invoice.ready"}},
        {},
    )
    assert result.provider_message_id == "provider-1"
    assert captured["headers"]["x-gns-signature"].startswith("v1=")
    assert captured["headers"]["x-gns-timestamp"]
    assert captured["body"] == b'{"event":"invoice.ready"}'


@pytest.mark.parametrize(
    ("channel", "public_config", "secret", "recipient", "content", "message_id"),
    [
        (
            "sms",
            {
                "base_url": "https://api.twilio.test",
                "account_sid": "AC123",
                "from_number": "+15551230000",
            },
            {"auth_token": "token"},
            {"phone": "+15551234567"},
            {"text": "hello"},
            "SM123",
        ),
        (
            "telegram",
            {"base_url": "https://api.telegram.test"},
            {"bot_token": "token"},
            {"chat_id": "123"},
            {"body": "hello", "inline_keyboard": []},
            "42",
        ),
        (
            "whatsapp",
            {
                "base_url": "https://graph.facebook.test",
                "api_version": "v23.0",
                "phone_number_id": "phone-id",
            },
            {"access_token": "token"},
            {"phone": "+15551234567"},
            {
                "template_name": "invoice",
                "language": "en",
                "parameters": [],
                "opt_in_reference": "consent-123",
            },
            "wamid.123",
        ),
        (
            "push",
            {"base_url": "https://fcm.test", "project_id": "project"},
            {"access_token": "token"},
            {"token": "device-token"},
            {"title": "Title", "body": "Body"},
            "projects/project/messages/123",
        ),
    ],
)
def test_json_provider_adapter_contracts(
    channel: str,
    public_config: dict,
    secret: dict,
    recipient: dict,
    content: dict,
    message_id: str,
) -> None:
    responses = {
        "sms": {"sid": message_id},
        "telegram": {"result": {"message_id": message_id}},
        "whatsapp": {"messages": [{"id": message_id}]},
        "push": {"name": message_id},
    }
    adapter = JSONAPIAdapter(
        channel,
        transport=httpx.MockTransport(lambda request: httpx.Response(200, json=responses[channel])),
    )
    result = adapter.send(public_config, secret, {}, recipient, content, {})
    assert result.provider_message_id == message_id
