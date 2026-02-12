"""Brain analyzer using Mistral-Nemo 12B via Ollama."""

from __future__ import annotations

import json
import logging
import os
from typing import Any

import httpx

from brain.prompts import ANALYSIS_PROMPT
from brain.schemas import AnalysisResult


class BrainAnalyzer:
    def __init__(
        self,
        model: str | None = None,
        ollama_host: str | None = None,
        timeout_seconds: float = 180.0,
    ) -> None:
        self.model = model or os.getenv("BRAIN_MODEL_NAME", "mistral-nemo-12b")
        self.ollama_host = (ollama_host or os.getenv("OLLAMA_HOST", "http://ollama:11434")).rstrip("/")
        self.timeout_seconds = timeout_seconds

    def analyze(self, episode_id: str, transcript_text: str, title: str | None = None) -> AnalysisResult:
        payload = {
            "episode_id": episode_id,
            "text": transcript_text,
            "title": title or "Untitled Episode",
        }
        try:
            response_text = self._call_ollama(transcript_text, title)
            data = json.loads(response_text)
            return AnalysisResult(
                episode_id=episode_id,
                core_thesis=data.get("core_thesis", ""),
                timestamped_topics=data.get("timestamped_topics", []),
                resources=data.get("resources", []),
                actionable_insights=data.get("actionable_insights", []),
            )
        except Exception as exc:  # pragma: no cover
            logging.warning("Brain analyzer fallback", extra={"error": str(exc)})
            return self._fallback(payload)

    def _call_ollama(self, transcript_text: str, title: str | None) -> str:
        prompt = f"{ANALYSIS_PROMPT}\n\nTitle: {title or 'Untitled'}\nTranscript:\n{transcript_text}"
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
        }
        url = f"{self.ollama_host}/api/generate"
        with httpx.Client(timeout=self.timeout_seconds) as client:
            resp = client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()
        return data.get("response", "{}")

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
