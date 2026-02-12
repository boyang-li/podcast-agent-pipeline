"""Telegram helper client."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import httpx


class TelegramClient:
    def __init__(self, bot_token: str, chat_id: str) -> None:
        self.bot_token = bot_token
        self.chat_id = chat_id
        self._base_url = f"https://api.telegram.org/bot{bot_token}"

    async def send_message(self, text: str, parse_mode: Optional[str] = None) -> None:
        payload = {"chat_id": self.chat_id, "text": text}
        if parse_mode:
            payload["parse_mode"] = parse_mode
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(f"{self._base_url}/sendMessage", json=payload)
            if response.status_code >= 400:
                logging.error("telegram send failed", extra={"status": response.status_code, "body": response.text})
                response.raise_for_status()

    async def send_document(self, file_path: Path | str, caption: Optional[str] = None) -> None:
        data = {"chat_id": self.chat_id}
        if caption:
            data["caption"] = caption
        async with httpx.AsyncClient(timeout=30.0) as client:
            path = Path(file_path)
            with path.open("rb") as document:
                files = {"document": (path.name, document)}
                response = await client.post(f"{self._base_url}/sendDocument", data=data, files=files)
            if response.status_code >= 400:
                logging.error(
                    "telegram document send failed",
                    extra={"status": response.status_code, "body": response.text},
                )
                response.raise_for_status()
