import os
from pathlib import Path

from fastapi import FastAPI, HTTPException, status

from ear.models import TranscribeRequest, TranscribeResponse
from ear.transcriber import TranscriptEngine
from shared.logging import configure_logging


MODEL_NAME = os.getenv("EAR_MODEL_NAME", "base.en")
EAR_DEVICE = os.getenv("EAR_DEVICE", "auto")


def create_app() -> FastAPI:
    configure_logging()
    app = FastAPI(title="Ear Transcription Service", version="0.2.0")
    engine = TranscriptEngine(model_name=MODEL_NAME, device=EAR_DEVICE)

    @app.get("/health", tags=["health"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/transcribe", response_model=TranscribeResponse, tags=["transcription"])
    def transcribe(payload: TranscribeRequest) -> TranscribeResponse:
        audio_path = resolve_audio_path(payload.audio_path)
        if not audio_path.exists():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Audio not found: {audio_path}")
        return engine.transcribe(payload.episode_id, str(audio_path), payload.language_hint)

    return app


app = create_app()


def audio_root() -> Path:
    return Path(os.getenv("PAP_STORAGE_ROOT", "/srv/pap"))


def resolve_audio_path(path_str: str) -> Path:
    path = Path(path_str)
    if not path.is_absolute():
        path = audio_root() / path
    resolved = path.resolve()
    root = audio_root().resolve()
    if root not in resolved.parents and resolved != root:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Audio path outside storage root")
    return resolved
