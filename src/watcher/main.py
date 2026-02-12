"""Watcher agent entrypoints (CLI + Prefect flow)."""

from __future__ import annotations

import argparse
import logging
import os
from pathlib import Path
from itertools import islice
from datetime import datetime

import httpx
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

try:
    from flows.pipeline import summarize_episode_flow
except ImportError:  # pragma: no cover
    summarize_episode_flow = None  # type: ignore

FEEDS_PATH = Path(os.getenv("WATCHER_FEEDS_PATH", "config/feeds.yaml"))
LEDGER_PATH = META_DIR / "downloads.db"
COURIER_ENDPOINT = os.getenv("COURIER_ENDPOINT", "http://127.0.0.1:8200")
WATCHER_MAX_RECENT = int(os.getenv("WATCHER_MAX_RECENT", "5"))


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
        items = list(islice(poll_youtube_feed(entry.channel_id, entry.channel_name), WATCHER_MAX_RECENT))
        downloaded: list[dict] = []
        queued: list[dict] = []
        pending: list[tuple[FeedItem, object]] = []
        submit = getattr(download_episode, "submit", None)
        for item in items:
            if HAS_PREFECT and callable(submit):
                pending.append((item, submit(item, settings)))
            else:
                path = download_episode(item, settings)
                _handle_download_result(item, path, downloaded, queued)
        for original_item, future in pending:
            path = getattr(future, "result", lambda: None)()
            _handle_download_result(original_item, path, downloaded, queued)
        _notify_watcher_status(entry.channel_name, downloaded, queued)


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
    watcher_flow(config_path=Path(args.config))


def _handle_download_result(item: FeedItem, path: str | None, downloaded: list[dict], queued: list[dict]) -> None:
    if not path:
        return
    payload = _episode_payload(item)
    downloaded.append(payload)
    if _maybe_trigger_summary(item, path):
        queued.append(payload)


def _episode_payload(item: FeedItem) -> dict:
    return {
        "episode_id": item.guid,
        "title": item.title,
        "published": item.published.isoformat(),
    }


def _maybe_trigger_summary(item: FeedItem, audio_path: str) -> bool:
    if summarize_episode_flow is None:
        logging.warning("summarize flow unavailable; skipping automatic summary", extra={"guid": item.guid})
        return False
    kwargs = {
        "episode_id": item.guid,
        "audio_path": audio_path,
        "title": item.title,
        "language_hint": None,
    }
    submit = getattr(summarize_episode_flow, "submit", None)
    if HAS_PREFECT and callable(submit):
        submit(**kwargs)
    else:
        summarize_episode_flow(**kwargs)  # type: ignore[misc]
    logging.info("queued summarize flow", extra={"guid": item.guid})
    return True


def _notify_watcher_status(channel: str, downloaded: list[dict], queued: list[dict]) -> None:
    payload = {
        "channel": channel,
        "downloaded": downloaded,
        "queued": queued,
    }
    try:
        with httpx.Client(timeout=10.0) as client:
            client.post(f"{COURIER_ENDPOINT}/watcher-status", json=payload)
    except httpx.HTTPError as exc:
        logging.error("failed to send watcher status", extra={"error": str(exc)})


if __name__ == "__main__":
    main()
