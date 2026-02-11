"""Markdown rendering utilities for summaries."""

from __future__ import annotations

from datetime import datetime, timezone
from textwrap import dedent
from typing import List


def render_summary(title: str, thesis: str, topics: List[str], insights: List[str]) -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    topics_md = "\n".join(f"- {t}" for t in topics)
    insights_md = "\n".join(f"1. {ins}" for ins in insights)
    return dedent(
        f"""
        # {title}

        _Generated at {now}_

        ## Core Thesis
        {thesis}

        ## Topics
        {topics_md or '- TBD'}

        ## Actionable Insights
        {insights_md or 'No insights available.'}
        """
    ).strip()
