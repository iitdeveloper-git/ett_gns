from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(frozen=True)
class SendResult:
    accepted: bool
    provider_message_id: str | None = None
    status: str = "provider_accepted"
    response_excerpt: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class AdapterError(RuntimeError):
    def __init__(
        self,
        code: str,
        message: str,
        *,
        retryable: bool,
        provider_status: int | None = None,
    ):
        self.code = code
        self.retryable = retryable
        self.provider_status = provider_status
        super().__init__(message)


class ChannelAdapter(Protocol):
    channel_name: str

    def validate_provider_config(
        self, public_config: dict[str, Any], secret: dict[str, Any]
    ) -> None: ...

    def validate_recipient(self, recipient: dict[str, Any]) -> None: ...

    def validate_content(self, content: dict[str, Any]) -> None: ...

    def send(
        self,
        public_config: dict[str, Any],
        secret: dict[str, Any],
        sender: dict[str, Any],
        recipient: dict[str, Any],
        content: dict[str, Any],
        metadata: dict[str, Any],
    ) -> SendResult: ...
