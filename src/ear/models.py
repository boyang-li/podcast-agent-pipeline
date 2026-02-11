"""Pydantic models for Ear API."""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel


class TranscribeRequest(BaseModel):
    episode_id: str
    audio_path: str
    language_hint: Optional[str] = None


class Segment(BaseModel):
    id: int
    start: float
    end: float
    text: str


class TranscribeResponse(BaseModel):
    episode_id: str
    language: str
    segments: List[Segment]
    confidence: float
