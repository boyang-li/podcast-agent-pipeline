"""FastAPI wrapper around CourierService."""

from __future__ import annotations

from typing import List
from datetime import datetime

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel

from courier.service import CourierService
from shared.config import Settings, load_settings
from shared.logging import configure_logging

settings: Settings = load_settings()
service = CourierService(settings.storage, settings.telegram)


class NotifyRequest(BaseModel):
    episode_id: str
    title: str
    thesis: str
    topics: List[str] = []
    insights: List[str] = []


class NotifyResponse(BaseModel):
    summary_path: str


class WatcherEpisode(BaseModel):
    episode_id: str
    title: str
    published: datetime
    audio_path: str | None = None


class WatcherStatusRequest(BaseModel):
    channel: str
    downloaded: List[WatcherEpisode] = []
    queued: List[WatcherEpisode] = []


def create_app() -> FastAPI:
    configure_logging()
    app = FastAPI(title="Courier Service", version="0.1.0")

    @app.get("/health", tags=["health"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/notify", response_model=NotifyResponse, tags=["notifications"])
    async def notify(request: NotifyRequest) -> NotifyResponse:
        if not request.thesis.strip():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Thesis is required")
        path = await service.send_summary(
            request.episode_id,
            request.title,
            request.thesis,
            request.topics,
            request.insights,
        )
        return NotifyResponse(summary_path=str(path))

    @app.post("/watcher-status", status_code=status.HTTP_204_NO_CONTENT, tags=["notifications"])
    async def watcher_status(request: WatcherStatusRequest) -> None:
        await service.send_watcher_update(
            request.channel,
            [episode.model_dump() for episode in request.downloaded],
            [episode.model_dump() for episode in request.queued],
        )
        return None

    return app


app = create_app()
