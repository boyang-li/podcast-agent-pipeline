"""Stub transcription engine (CPU mock)."""

from __future__ import annotations

import logging
import random
from pathlib import Path
from typing import Any, Optional

WhisperModelType = Any
try:  # pragma: no cover - optional runtime dependency
    from faster_whisper import WhisperModel as RuntimeWhisperModel  # type: ignore[attr-defined]
except Exception:  # pragma: no cover
    RuntimeWhisperModel = None

from ear.models import Segment, TranscribeResponse


class TranscriptEngine:
    """GPU-aware transcription engine (falls back to stub)."""

    def __init__(self, model_name: str = "base.en", device: str = "auto") -> None:
        self.model_name = model_name
        self.device = device
        self._model: Optional[WhisperModelType] = None
        if RuntimeWhisperModel is not None:
            try:
                self._model = RuntimeWhisperModel(model_name, device=device)
                logging.info("Loaded faster-whisper model", extra={"model": model_name, "device": device})
            except Exception as exc:  # pragma: no cover - fallback for local tests
                logging.warning("Failed to load faster-whisper model, using stub", extra={"error": str(exc)})
                self._model = None

    def transcribe(self, episode_id: str, audio_path: str, language_hint: str | None = None) -> TranscribeResponse:
        if self._model is None:
            return self._stub_transcription(episode_id, audio_path, language_hint)

        segments_iter, info = self._model.transcribe(audio_path, language=language_hint)
        segments = [
            Segment(id=i, start=seg.start, end=seg.end, text=seg.text)
            for i, seg in enumerate(segments_iter)
        ]
        confidence = round(info.language_probability, 3)
        return TranscribeResponse(
            episode_id=episode_id,
            language=info.language or language_hint or "en",
            segments=segments,
            confidence=confidence,
        )

    def _stub_transcription(self, episode_id: str, audio_path: str, language_hint: str | None) -> TranscribeResponse:
        path = Path(audio_path)
        text = path.stem.replace("_", " ")
        random.seed(hash(audio_path) & 0xFFFFFFFF)
        segments = [
            Segment(id=0, start=0.0, end=15.0, text=f"Intro (stub): {text}"),
            Segment(id=1, start=15.0, end=45.0, text="Main discussion placeholder."),
        ]
        confidence = round(0.7 + random.random() * 0.2, 3)
        return TranscribeResponse(
            episode_id=episode_id,
            language=language_hint or "en",
            segments=segments,
            confidence=confidence,
        )
