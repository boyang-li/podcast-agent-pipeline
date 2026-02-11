from courier.markdown import render_summary


def test_render_summary_contains_sections():
    md = render_summary("Episode", "Thesis", ["Topic A"], ["Insight 1"])
    assert "# Episode" in md
    assert "## Core Thesis" in md
    assert "Topic A" in md
