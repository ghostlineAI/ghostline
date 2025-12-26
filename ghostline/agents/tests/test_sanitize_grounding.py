import os

from orchestrator.subgraphs import ChapterSubgraph, SubgraphConfig


def test_sanitize_grounding_non_destructive_by_default(monkeypatch):
    monkeypatch.delenv("GHOSTLINE_DESTRUCTIVE_SANITIZER", raising=False)

    sg = ChapterSubgraph(config=SubgraphConfig())
    content = (
        "I don't want this altered.\n\n"
        "This is a substantive paragraph with no citations and it should stay, even if it's risky.\n\n"
        "This paragraph cites a quote but does not include it in prose "
        '[citation: mentalhealth1.pdf - "Taking a step back"] and should not be rewritten.'
    )

    assert sg._sanitize_grounding(content) == content.strip()


def test_sanitize_grounding_can_enable_legacy_destructive_mode(monkeypatch):
    monkeypatch.setenv("GHOSTLINE_DESTRUCTIVE_SANITIZER", "1")

    sg = ChapterSubgraph(config=SubgraphConfig())
    content = (
        "This uncited paragraph has enough words that the legacy sanitizer would drop it entirely.\n\n"
        'This cites [citation: mentalhealth1.pdf - "Exact quote"] but the quote is not in prose.'
    )

    out = sg._sanitize_grounding(content)
    assert out != content.strip()
    assert "uncited paragraph" not in out.lower()
    assert '"Exact quote"' in out


