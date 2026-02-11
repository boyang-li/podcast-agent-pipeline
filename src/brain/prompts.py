"""Prompt templates for Brain analyzer."""

from __future__ import annotations

ANALYSIS_PROMPT = """
You are the Brain module of Podcast Agent Pipeline. Given transcript text, summarize:
- Core thesis (2 sentences)
- Up to 5 timestamped topics (mm:ss format)
- Up to 3 resources (title + URL)
- Up to 3 actionable insights
Return strict JSON matching this schema:
{
  "core_thesis": "...",
  "timestamped_topics": [{"title": "...", "timestamp": 123.4}],
  "resources": [{"title": "...", "url": "https://"}],
  "actionable_insights": ["..."]
}
"""
