from __future__ import annotations

import base64
import hashlib
import json
from typing import Any, cast

from cryptography.fernet import Fernet, InvalidToken

from ett_gns_app.settings import Settings


class SecretStore:
    """Encrypted local secret store boundary.

    Production can replace this implementation with a cloud secret-manager adapter
    while retaining provider records as secret references.
    """

    def __init__(self, settings: Settings):
        raw_key = settings.provider_secret_key or settings.api_key_pepper
        key = base64.urlsafe_b64encode(hashlib.sha256(raw_key.encode()).digest())
        self._fernet = Fernet(key)

    def encrypt(self, secret: dict[str, Any]) -> bytes:
        return self._fernet.encrypt(
            json.dumps(secret, sort_keys=True, separators=(",", ":")).encode()
        )

    def decrypt(self, ciphertext: bytes | None) -> dict[str, Any]:
        if not ciphertext:
            return {}
        try:
            return cast(dict[str, Any], json.loads(self._fernet.decrypt(ciphertext)))
        except (InvalidToken, json.JSONDecodeError) as exc:
            raise ValueError("Provider secret cannot be decrypted") from exc
