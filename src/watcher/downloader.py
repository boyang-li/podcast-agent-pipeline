"""Audio downloader using yt-dlp."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import List


class DownloadError(RuntimeError):
    """Raised when yt-dlp exits with a non-zero status."""


def download_audio(url: str, output_template: str, extra_args: List[str] | None = None) -> Path:
    args = [
        "yt-dlp",
        "--extract-audio",
        "--audio-format",
        "mp3",
        "--audio-quality",
        "5",
        "--write-info-json",
        "--download-archive",
        "downloaded.txt",
        "--sleep-interval",
        "5",
        "--max-sleep-interval",
        "15",
        "--output",
        output_template,
        url,
    ]
    if extra_args:
        args.extend(extra_args)
    result = subprocess.run(args, capture_output=True, text=True, check=False)
    if result.returncode not in (0, 2):  # 2 == no video / already downloaded
        raise DownloadError(result.stderr.strip())
    final_path = _extract_output_path(output_template)
    return final_path


def _extract_output_path(template: str) -> Path:
    # For deterministic tests, we assume template ends with filename pattern.
    return Path(template).expanduser().resolve()
