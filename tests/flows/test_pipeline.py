from flows.pipeline import podcast_agent_pipeline


def test_pipeline_flow(monkeypatch, tmp_path):
    def mock_download(url, feed_id, guid, template):
        file_path = tmp_path / f"{guid}.mp3"
        file_path.write_text("audio")
        return str(file_path)

    monkeypatch.setattr("flows.pipeline.download_task", mock_download)
    async def fake_send_message(self, text, parse_mode=None):
        return None

    monkeypatch.setattr("courier.telegram.TelegramClient.send_message", fake_send_message)
    result = podcast_agent_pipeline("https://example.com/episode", "feed", "guid123", "~/output/%(ext)s")
    assert result.endswith(".md")
