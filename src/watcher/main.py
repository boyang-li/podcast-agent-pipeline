"""Watcher agent entrypoints (CLI + Prefect flow)."""

from __future__ import annotations

import argparse
import logging
import os
from pathlib import Path

try:
    from prefect import flow, task  # type: ignore
    HAS_PREFECT = True
except ImportError:  # pragma: no cover
    HAS_PREFECT = False

    def _identity_decorator(func=None, **kwargs):
        if func is None:
            def wrapper(inner):
                return inner
            return wrapper
        return func

    def task(func=None, **kwargs):
        return _identity_decorator(func, **kwargs)

    def flow(func=None, **kwargs):
        return _identity_decorator(func, **kwargs)

from shared.config import Settings, load_settings
from shared.logging import configure_logging
from shared.paths import META_DIR, RAW_AUDIO_DIR, ensure_storage_dirs
from watcher.config import WatcherConfig, iter_youtube_entries
from watcher.downloader import download_audio
from watcher.ledger import DownloadLedger
from watcher.poller import FeedItem, poll_rss_feed, poll_youtube_feed

FEEDS_PATH = Path(os.getenv("WATCHER_FEEDS_PATH", "config/feeds.yaml"))
LEDGER_PATH = META_DIR / "downloads.db"


def _output_template(channel_name: str, guid: str) -> str:
    safe_channel = channel_name.replace(" ", "_")
    return str(RAW_AUDIO_DIR / safe_channel / f"{guid}.%(ext)s")


@task(name="download_episode")
def download_episode(item: FeedItem, settings: Settings) -> str | None:
    ensure_storage_dirs()
    ledger = DownloadLedger(LEDGER_PATH)
    if ledger.has_guid(item.guid):
        logging.info("skipping already downloaded episode", extra={"guid": item.guid})
        ledger.close()
        return None
    template = _output_template(item.feed_id, item.guid)
    path = download_audio(item.link, template)
    ledger.record(item.guid, item.feed_id, path)
    ledger.close()
    logging.info("downloaded episode", extra={"guid": item.guid, "path": str(path)})
    return str(path)


@flow(name="watcher_flow")
def watcher_flow(config_path: Path = FEEDS_PATH) -> None:
    configure_logging()
    settings = load_settings()
    config = WatcherConfig.load(config_path)
    _dispatch_youtube(config, settings)
    _dispatch_rss(config, settings)


def _dispatch_youtube(config: WatcherConfig, settings: Settings) -> None:
    for entry in iter_youtube_entries(config):
        for item in poll_youtube_feed(entry.channel_id, entry.channel_name):
            submit = getattr(download_episode, "submit", None)
            if HAS_PREFECT and callable(submit):
                submit(item, settings)
            else:
                download_episode(item, settings)


def _dispatch_rss(config: WatcherConfig, settings: Settings) -> None:
    for url in config.rss_feeds:
        for item in poll_rss_feed(url, url):
            submit = getattr(download_episode, "submit", None)
            if HAS_PREFECT and callable(submit):
                submit(item, settings)
            else:
                download_episode(item, settings)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run watcher tasks")
    parser.add_argument("--config", default=str(FEEDS_PATH), help="Path to feeds YAML")
    args = parser.parse_args()
    watcher_flow(Path(args.config))


if __name__ == "__main__":
    main()
