"""File-system path helpers."""

from __future__ import annotations

from pathlib import Path
import os


PAP_ROOT = Path(os.getenv("PAP_STORAGE_ROOT", "/srv/pap")).resolve()
RAW_AUDIO_DIR = PAP_ROOT / "raw"
TRANSCRIPTS_DIR = PAP_ROOT / "transcripts"
SUMMARIES_DIR = PAP_ROOT / "summaries"
META_DIR = PAP_ROOT / "meta"


def ensure_storage_dirs() -> None:
    for directory in (RAW_AUDIO_DIR, TRANSCRIPTS_DIR, SUMMARIES_DIR, META_DIR):
        directory.mkdir(parents=True, exist_ok=True)
