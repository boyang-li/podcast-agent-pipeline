"""Common Pydantic models."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, HttpUrl


class EpisodeMetadata(BaseModel):
    feed: str
    title: str
    description: Optional[str]
    published_at: datetime
    audio_url: HttpUrl
    duration_seconds: Optional[int]
    guid: str


class TranscriptSegment(BaseModel):
    id: int
    start: float
    end: float
    text: str


class TranscriptResult(BaseModel):
    episode_id: str
    language: str
    segments: List[TranscriptSegment]
    confidence: float
