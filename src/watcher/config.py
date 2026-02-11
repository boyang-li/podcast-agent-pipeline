"""Watcher-specific configuration loaders."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List

from shared.config import WatcherFeedConfig


@dataclass(slots=True)
class FeedEntry:
    channel_id: str
    channel_name: str
    poll_interval_minutes: int


@dataclass(slots=True)
class WatcherConfig:
    youtube_feeds: List[FeedEntry]
    rss_feeds: List[str]
    defaults: dict

    @classmethod
    def load(cls, config_path: Path) -> "WatcherConfig":
        data = WatcherFeedConfig.from_yaml(config_path).feeds
        yt_entries = [
            FeedEntry(
                channel_id=item["channel_id"],
                channel_name=item["channel_name"],
                poll_interval_minutes=item.get("poll_interval_minutes", 60),
            )
            for item in data.get("youtube", [])
        ]
        rss_list = [item["url"] for item in data.get("rss", [])]
        return cls(
            youtube_feeds=yt_entries,
            rss_feeds=rss_list,
            defaults=data.get("defaults", {}),
        )


def iter_youtube_entries(config: WatcherConfig) -> Iterable[FeedEntry]:
    yield from config.youtube_feeds
