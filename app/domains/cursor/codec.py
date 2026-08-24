# app/redis/cursor_store.py

import base64
import json
import os
import time
from typing import Any

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.config import settings


class CursorStore:
    """
    Stateless encrypted cursor storage.

    Cursor data is encrypted into a self-contained token.
    Nothing is stored in Redis.

    The store exposes add_cursor/get_cursor/delete_cursor for
    compatibility with the previous Redis-backed implementation.
    """

    def __init__(self, ttl: int = 60 * 60):
        secret_key = settings.CURSOR_SECRET_KEY

        if not secret_key:
            raise RuntimeError(
                "CURSOR_SECRET_KEY is not configured"
            )

        try:
            self.key = base64.urlsafe_b64decode(secret_key)
        except Exception as exc:
            raise RuntimeError(
                "CURSOR_SECRET_KEY must be a valid base64url encoded key"
            ) from exc

        if len(self.key) not in (16, 24, 32):
            raise RuntimeError(
                "CURSOR_SECRET_KEY must decode to 16, 24, or 32 bytes"
            )

        self.ttl = ttl

    def encode(self, cursor: dict[str, Any]) -> str:
        """
        Encrypt cursor data and return an opaque token.
        """

        now = int(time.time())

        payload = {
            "v": 1,
            "iat": now,
            "exp": now + self.ttl,
            "data": cursor,
        }

        plaintext = json.dumps(
            payload,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode()

        nonce = os.urandom(12)

        ciphertext = AESGCM(self.key).encrypt(
            nonce,
            plaintext,
            None,
        )

        return base64.urlsafe_b64encode(
            nonce + ciphertext
        ).decode()

    def decode(self, token: str) -> dict[str, Any]:
        """
        Decrypt and validate an encrypted cursor.
        """

        try:
            raw = base64.urlsafe_b64decode(token)

            if len(raw) < 13:
                raise ValueError("Invalid cursor")

            nonce = raw[:12]
            ciphertext = raw[12:]

            plaintext = AESGCM(self.key).decrypt(
                nonce,
                ciphertext,
                None,
            )

            payload = json.loads(plaintext)

        except Exception as exc:
            raise ValueError("Invalid cursor") from exc

        if payload.get("v") != 1:
            raise ValueError("Unsupported cursor version")

        if payload.get("exp", 0) < int(time.time()):
            raise ValueError("Cursor expired")

        data = payload.get("data")

        if not isinstance(data, dict):
            raise ValueError("Invalid cursor payload")

        return data

    # ------------------------------------------------------------------
    # Compatibility API
    # ------------------------------------------------------------------

    async def add_cursor(
        self,
        cursor_key: str,
        cursor: dict[str, Any],
    ) -> str:
        """
        Create an encrypted cursor.

        `cursor_key` is accepted for compatibility with the old
        Redis-backed implementation but is not stored.
        """

        return self.encode(cursor)

    async def get_cursor(
        self,
        cursor_key: str,
    ) -> dict[str, Any] | None:
        """
        Decode an encrypted cursor.

        `cursor_key` should now contain the encrypted cursor token.
        """

        if not cursor_key:
            return None

        try:
            return self.decode(cursor_key)
        except ValueError:
            return None

    async def delete_cursor(
        self,
        cursor_key: str,
    ) -> None:
        """
        Stateless cursors cannot be deleted/revoked because they are
        not stored server-side.

        Kept as a no-op for compatibility with existing callers.
        """

        return None