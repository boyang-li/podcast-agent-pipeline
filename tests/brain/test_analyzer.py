from brain.analyzer import BrainAnalyzer


def test_analyzer_fallback(monkeypatch):
    monkeypatch.setattr("brain.analyzer.ollama", None)
    analyzer = BrainAnalyzer()
    result = analyzer.analyze("ep1", "Hello world transcript")
    assert result.episode_id == "ep1"
    assert result.actionable_insights
