"""FastAPI application for Ear transcription service."""

from __future__ import annotations

from fastapi import FastAPI, HTTPException, status

from ear.models import TranscribeRequest, TranscribeResponse
from ear.transcriber import TranscriptEngine
from shared.logging import configure_logging


def create_app() -> FastAPI:
    configure_logging()
    app = FastAPI(title="Ear Transcription Service", version="0.1.0")
    engine = TranscriptEngine()

    @app.get("/health", tags=["health"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/transcribe", response_model=TranscribeResponse, tags=["transcription"])
    def transcribe(payload: TranscribeRequest) -> TranscribeResponse:
        try:
            return engine.transcribe(payload.episode_id, payload.audio_path, payload.language_hint)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return app


app = create_app()
