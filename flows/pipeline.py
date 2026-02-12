"""Prefect flow for running Ear → Brain → Courier services."""

from __future__ import annotations

import os
from typing import List

import httpx

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


EAR_ENDPOINT = os.getenv("EAR_ENDPOINT", "http://192.168.2.82:8000")
BRAIN_ENDPOINT = os.getenv("BRAIN_ENDPOINT", "http://192.168.2.82:8100")
COURIER_ENDPOINT = os.getenv("COURIER_ENDPOINT", "http://192.168.2.81:8200")


@task(name="request_transcript")
def transcribe_task(episode_id: str, audio_path: str, language_hint: str | None = None) -> dict:
    payload = {
        "episode_id": episode_id,
        "audio_path": audio_path,
        "language_hint": language_hint,
    }
    with httpx.Client(timeout=300.0) as client:
        resp = client.post(f"{EAR_ENDPOINT}/transcribe", json=payload)
        resp.raise_for_status()
        return resp.json()


@task(name="summarize_transcript")
def analyze_task(episode_id: str, title: str, transcript_text: str) -> dict:
    payload = {
        "episode_id": episode_id,
        "title": title,
        "transcript": transcript_text,
    }
    with httpx.Client(timeout=300.0) as client:
        resp = client.post(f"{BRAIN_ENDPOINT}/summarize", json=payload)
        resp.raise_for_status()
        return resp.json()


@task(name="notify_summary")
def deliver_task(episode_id: str, title: str, thesis: str, topics: List[str], insights: List[str]) -> str:
    payload = {
        "episode_id": episode_id,
        "title": title,
        "thesis": thesis,
        "topics": topics,
        "insights": insights,
    }
    with httpx.Client(timeout=120.0) as client:
        resp = client.post(f"{COURIER_ENDPOINT}/notify", json=payload)
        resp.raise_for_status()
        data = resp.json()
    return data.get("summary_path", "")


def _segments_to_text(transcript: dict) -> str:
    return "\n".join(seg.get("text", "") for seg in transcript.get("segments", []))


@flow(name="summarize_episode_flow")
def summarize_episode_flow(
    episode_id: str,
    audio_path: str,
    title: str,
    language_hint: str | None = None,
) -> str:
    transcript = transcribe_task(episode_id, audio_path, language_hint)
    analysis = analyze_task(episode_id, title, _segments_to_text(transcript))
    thesis = analysis.get("core_thesis", title)
    topics = [topic.get("title", "") for topic in analysis.get("timestamped_topics", [])]
    insights = analysis.get("actionable_insights", [])
    return deliver_task(episode_id, title, thesis, topics, insights)


if __name__ == "__main__":  # pragma: no cover
    import argparse

    parser = argparse.ArgumentParser(description="Summarize a podcast episode")
    parser.add_argument("episode_id", help="Unique episode identifier")
    parser.add_argument("audio_path", help="Path to local audio file (mp3)")
    parser.add_argument("title", help="Episode title")
    parser.add_argument("--language", default=None, help="Optional language hint (e.g., en)")
    args = parser.parse_args()

    summarize_episode_flow(args.episode_id, args.audio_path, args.title, language_hint=args.language)
