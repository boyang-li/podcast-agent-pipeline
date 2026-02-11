"""Pydantic schemas for Brain outputs."""

from __future__ import annotations

from typing import List

from pydantic import BaseModel


class TimestampedTopic(BaseModel):
    title: str
    timestamp: float


class ResourceItem(BaseModel):
    title: str
    url: str


class AnalysisResult(BaseModel):
    episode_id: str
    core_thesis: str
    timestamped_topics: List[TimestampedTopic]
    resources: List[ResourceItem]
    actionable_insights: List[str]
