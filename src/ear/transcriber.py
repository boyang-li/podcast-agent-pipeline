"""Stub transcription engine (CPU mock)."""

from __future__ import annotations

import random
from pathlib import Path

from ear.models import Segment, TranscribeResponse


class TranscriptEngine:
    """Minimal engine placeholder until faster-whisper integration lands."""

    def __init__(self, default_language: str = "en") -> None:
        self.default_language = default_language

    def transcribe(self, episode_id: str, audio_path: str, language_hint: str | None = None) -> TranscribeResponse:
        path = Path(audio_path)
        text = path.stem.replace("_", " ")
        random.seed(hash(audio_path) & 0xFFFFFFFF)
        segments = [
            Segment(id=0, start=0.0, end=15.0, text=f"Intro: {text}"),
            Segment(id=1, start=15.0, end=45.0, text="Main discussion placeholder."),
        ]
        confidence = round(0.7 + random.random() * 0.2, 3)
        return TranscribeResponse(
            episode_id=episode_id,
            language=language_hint or self.default_language,
            segments=segments,
            confidence=confidence,
        )
