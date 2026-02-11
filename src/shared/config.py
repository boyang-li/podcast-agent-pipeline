"""Configuration helpers for the Podcast Agent Pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import os
from typing import Any, Dict

import yaml


def _env(key: str, default: str | None = None) -> str:
    value = os.getenv(key)
    if value is not None:
        return value
    if default is not None:
        return default
    raise KeyError(f"Missing required environment variable: {key}")


@dataclass(slots=True)
class PrefectConfig:
    api_url: str = field(default_factory=lambda: _env("PREFECT_API_URL", "http://127.0.0.1:4200/api"))
    work_pool_default: str = field(default_factory=lambda: os.getenv("PREFECT_POOL_DEFAULT", "default"))
    work_pool_gpu: str = field(default_factory=lambda: os.getenv("PREFECT_POOL_GPU", "gpu"))


@dataclass(slots=True)
class StoragePaths:
    root: Path = field(default_factory=lambda: Path(os.getenv("PAP_STORAGE_ROOT", "/srv/pap")))

    @property
    def raw_audio(self) -> Path:
        return self.root / "raw"

    @property
    def transcripts(self) -> Path:
        return self.root / "transcripts"

    @property
    def summaries(self) -> Path:
        return self.root / "summaries"

    @property
    def meta(self) -> Path:
        return self.root / "meta"


@dataclass(slots=True)
class TelegramConfig:
    bot_token: str = field(default_factory=lambda: _env("TELEGRAM_BOT_TOKEN"))
    chat_id: str = field(default_factory=lambda: _env("TELEGRAM_CHAT_ID"))


@dataclass(slots=True)
class WatcherFeedConfig:
    feeds: Dict[str, Any]

    @classmethod
    def from_yaml(cls, path: Path) -> "WatcherFeedConfig":
        with path.open("r", encoding="utf-8") as fp:
            data = yaml.safe_load(fp)
        return cls(feeds=data)


@dataclass(slots=True)
class Settings:
    prefect: PrefectConfig = field(default_factory=PrefectConfig)
    storage: StoragePaths = field(default_factory=StoragePaths)
    telegram: TelegramConfig = field(default_factory=TelegramConfig)


def load_settings() -> Settings:
    return Settings()
