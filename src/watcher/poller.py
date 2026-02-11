"""Feed polling utilities for Watcher."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Iterable, Iterator, Optional

try:
    import feedparser  # type: ignore
except ImportError:  # pragma: no cover
    feedparser = None  # type: ignore


@dataclass(slots=True)
class FeedItem:
    feed_id: str
    title: str
    link: str
    published: datetime
    guid: str
    description: Optional[str]


YOUTUBE_TEMPLATE = "https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"


def poll_youtube_feed(channel_id: str, channel_name: str) -> Iterator[FeedItem]:
    if feedparser is None:
        raise RuntimeError("feedparser dependency not installed")
    url = YOUTUBE_TEMPLATE.format(channel_id=channel_id)
    parsed = feedparser.parse(url)
    for entry in parsed.entries:
        published = getattr(entry, "published", "")
        yield FeedItem(
            feed_id=channel_name,
            title=entry.title,
            link=entry.link,
            published=datetime(*entry.published_parsed[:6]) if entry.get("published_parsed") else datetime.utcnow(),
            guid=entry.id,
            description=getattr(entry, "summary", None),
        )


def poll_rss_feed(url: str, feed_id: str) -> Iterable[FeedItem]:
    if feedparser is None:
        raise RuntimeError("feedparser dependency not installed")
    parsed = feedparser.parse(url)
    for entry in parsed.entries:
        yield FeedItem(
            feed_id=feed_id,
            title=entry.title,
            link=entry.link,
            published=datetime(*entry.published_parsed[:6]) if entry.get("published_parsed") else datetime.utcnow(),
            guid=entry.id,
            description=getattr(entry, "summary", None),
        )
