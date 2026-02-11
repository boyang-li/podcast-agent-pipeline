"""Primary Prefect flow wiring Watcher -> Ear -> Brain -> Courier."""

from __future__ import annotations

from pathlib import Path

try:
    from prefect import flow, task  # type: ignore
except ImportError:  # pragma: no cover
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

from brain.analyzer import BrainAnalyzer
from courier.service import CourierService, send_summary_sync
from ear.transcriber import TranscriptEngine
from shared.config import Settings, load_settings
from shared.paths import META_DIR
from watcher.downloader import download_audio
from watcher.ledger import DownloadLedger


@task
def download_task(url: str, feed_id: str, guid: str, template: str) -> str:
    ledger = DownloadLedger(META_DIR / "downloads.db")
    if ledger.has_guid(guid):
        return str(template)
    path = download_audio(url, template)
    ledger.record(guid, feed_id, Path(path))
    ledger.close()
    return str(path)


@task
def transcribe_task(episode_id: str, audio_path: str) -> str:
    engine = TranscriptEngine()
    result = engine.transcribe(episode_id, audio_path)
    return "\n".join(segment.text for segment in result.segments)


@task
def analyze_task(episode_id: str, transcript_text: str) -> dict:
    analyzer = BrainAnalyzer()
    result = analyzer.analyze(episode_id, transcript_text)
    return result.model_dump()


@task
def deliver_task(payload: dict, settings: Settings) -> str:
    courier = CourierService(settings.storage, settings.telegram)
    path = send_summary_sync(
        courier,
        payload["episode_id"],
        title=payload.get("core_thesis", "Untitled Episode"),
        thesis=payload.get("core_thesis", ""),
        topics=[topic.get("title", "") for topic in payload.get("timestamped_topics", [])],
        insights=payload.get("actionable_insights", []),
    )
    return str(path)


@flow(name="podcast_agent_pipeline")
def podcast_agent_pipeline(episode_url: str, feed_id: str, guid: str, template: str) -> str:
    settings = load_settings()
    audio_path = download_task(episode_url, feed_id, guid, template)
    transcript_text = transcribe_task(guid, audio_path)
    analysis = analyze_task(guid, transcript_text)
    return deliver_task(analysis, settings)
