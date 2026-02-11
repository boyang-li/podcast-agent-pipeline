"""Courier service orchestrating persistence and notifications."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import List

from courier.markdown import render_summary
from courier.telegram import TelegramClient
from shared.config import StoragePaths, TelegramConfig


class CourierService:
    def __init__(self, storage: StoragePaths, telegram: TelegramConfig) -> None:
        self.storage = storage
        self.telegram_client = TelegramClient(telegram.bot_token, telegram.chat_id)

    def persist_summary(self, episode_id: str, title: str, thesis: str, topics: List[str], insights: List[str]) -> Path:
        content = render_summary(title, thesis, topics, insights)
        summaries_dir = self.storage.summaries
        summaries_dir.mkdir(parents=True, exist_ok=True)
        output_path = summaries_dir / f"{episode_id}.md"
        output_path.write_text(content, encoding="utf-8")
        return output_path

    async def notify(self, content: str) -> None:
        await self.telegram_client.send_message(content)

    async def send_summary(self, episode_id: str, title: str, thesis: str, topics: List[str], insights: List[str]) -> Path:
        path = self.persist_summary(episode_id, title, thesis, topics, insights)
        await self.notify(f"New summary for *{title}* saved at {path}")
        return path


def send_summary_sync(service: CourierService, episode_id: str, title: str, thesis: str, topics: List[str], insights: List[str]) -> Path:
    return asyncio.run(service.send_summary(episode_id, title, thesis, topics, insights))
