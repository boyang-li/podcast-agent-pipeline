from datetime import datetime, timezone

from watcher.poller import FeedItem


def test_feed_item_fields() -> None:
    item = FeedItem(
        feed_id="channel",
        title="Episode",
        link="https://",
        published=datetime.now(timezone.utc),
        guid="g1",
        description="desc",
    )
    assert item.feed_id == "channel"
    assert item.title == "Episode"
