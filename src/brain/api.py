"""FastAPI service for Brain analyzer."""

from __future__ import annotations

import os
from typing import Optional

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel

from brain.analyzer import BrainAnalyzer
from brain.schemas import AnalysisResult
from shared.logging import configure_logging


class SummarizeRequest(BaseModel):
    episode_id: str
    transcript: str
    title: Optional[str] = None


def create_app() -> FastAPI:
    configure_logging()
    app = FastAPI(title="Brain Summarization Service", version="0.1.0")
    analyzer = BrainAnalyzer(
        model=os.getenv("BRAIN_MODEL_NAME"),
        ollama_host=os.getenv("OLLAMA_HOST"),
    )

    @app.get("/health", tags=["health"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/summarize", response_model=AnalysisResult, tags=["analysis"])
    def summarize(request: SummarizeRequest) -> AnalysisResult:
        if not request.transcript.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Transcript text is required"
            )
        return analyzer.analyze(request.episode_id, request.transcript, title=request.title)

    return app


app = create_app()
