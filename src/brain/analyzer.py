"""Brain analyzer stub using Ollama when available."""

from __future__ import annotations

import json
import logging
from typing import Any

try:
    import ollama  # type: ignore
except ImportError:  # pragma: no cover
    ollama = None  # type: ignore

from brain.prompts import ANALYSIS_PROMPT
from brain.schemas import AnalysisResult


class BrainAnalyzer:
    def __init__(self, model: str = "qwen2.5-coder:7b", fallback_language: str = "en") -> None:
        self.model = model
        self.fallback_language = fallback_language

    def analyze(self, episode_id: str, transcript_text: str) -> AnalysisResult:
        payload = {
            "episode_id": episode_id,
            "text": transcript_text,
        }
        if ollama is None:
            logging.warning("ollama python client not installed; using fallback analysis")
            return self._fallback(payload)
        response = ollama.generate(model=self.model, prompt=f"{ANALYSIS_PROMPT}\n\nText:\n{transcript_text}")
        data = json.loads(response["response"])
        return AnalysisResult(
            episode_id=episode_id,
            core_thesis=data.get("core_thesis", ""),
            timestamped_topics=data.get("timestamped_topics", []),
            resources=data.get("resources", []),
            actionable_insights=data.get("actionable_insights", []),
        )

    def _fallback(self, payload: dict[str, Any]) -> AnalysisResult:
        text = payload["text"]
        lines = text.splitlines()
        topics = [line.strip() for line in lines if line.strip()][:3]
        return AnalysisResult(
            episode_id=payload["episode_id"],
            core_thesis=topics[0] if topics else "Unable to determine thesis",
            timestamped_topics=[],
            resources=[],
            actionable_insights=["Review full transcript with production model"],
        )
