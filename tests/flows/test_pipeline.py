from flows.pipeline import summarize_episode_flow


def test_summarize_episode_flow(monkeypatch):
    monkeypatch.setattr(
        "flows.pipeline.transcribe_task",
        lambda episode_id, audio_path, language_hint=None: {"segments": [{"text": "Hello world"}]},
    )
    monkeypatch.setattr(
        "flows.pipeline.analyze_task",
        lambda episode_id, title, transcript_text: {
            "episode_id": episode_id,
            "core_thesis": "Test thesis",
            "timestamped_topics": [],
            "actionable_insights": ["insight"],
        },
    )

    def fake_deliver(episode_id, title, thesis, topics, insights):
        return "/srv/pap/summaries/test.md"

    monkeypatch.setattr("flows.pipeline.deliver_task", fake_deliver)

    result = summarize_episode_flow("ep1", "/srv/pap/raw/foo.mp3", "Test title")
    assert result.endswith("test.md")
