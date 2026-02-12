from brain.analyzer import BrainAnalyzer


def test_analyzer_fallback(monkeypatch):
    def boom(*args, **kwargs):
        raise RuntimeError("ollama unavailable")

    monkeypatch.setattr("brain.analyzer.BrainAnalyzer._call_ollama", lambda self, transcript, title: boom())
    analyzer = BrainAnalyzer()
    result = analyzer.analyze("ep1", "Hello world transcript")
    assert result.episode_id == "ep1"
    assert result.actionable_insights
