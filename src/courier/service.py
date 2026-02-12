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

    async def send_summary(self, episode_id: str, title: str, thesis: str, topics: List[str], insights: List[str]) -> Path:
        path = self.persist_summary(episode_id, title, thesis, topics, insights)
        preview = _build_preview_message(title, thesis, topics, insights, path)
        await self.telegram_client.send_message(preview)
        await self.telegram_client.send_document(path, caption=f"Full notes • {title}")
        return path


def send_summary_sync(service: CourierService, episode_id: str, title: str, thesis: str, topics: List[str], insights: List[str]) -> Path:
    return asyncio.run(service.send_summary(episode_id, title, thesis, topics, insights))


_PREVIEW_BULLET_LIMIT = 3


def _build_preview_message(title: str, thesis: str, topics: List[str], insights: List[str], path: Path) -> str:
    sections: List[str] = [f"{title}", f"Core thesis: {thesis}"]
    topics_section = _format_list_section("Topics", topics)
    if topics_section:
        sections.append(topics_section)
    insights_section = _format_list_section("Insights", insights)
    if insights_section:
        sections.append(insights_section)
    sections.append(f"Full Markdown saved at: {path}")
    return "\n\n".join(sections)


def _format_list_section(label: str, values: List[str]) -> str:
    if not values:
        return ""
    subset = values[:_PREVIEW_BULLET_LIMIT]
    bullet_lines = "\n".join(f"• {item}" for item in subset)
    remainder = len(values) - _PREVIEW_BULLET_LIMIT
    extra = f"\n… (+{remainder} more)" if remainder > 0 else ""
    return f"{label}:\n{bullet_lines}{extra}"
