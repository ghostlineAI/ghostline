from orchestrator.subgraphs import ChapterSubgraph, SubgraphConfig


def test_style_gate_flags_em_dash_overuse():
    sg = ChapterSubgraph(config=SubgraphConfig())
    # ~100 words with many em-dashes should trigger the dash density gate
    words = "word " * 100
    content = f"{words} — {words} — {words} — {words} — {words}"
    issues = sg._compute_style_issues(content)
    assert any("em/en-dashes" in i for i in issues)


def test_style_gate_quote_presence_message_does_not_require_quotation_marks():
    sg = ChapterSubgraph(config=SubgraphConfig())
    content = (
        "This is a substantive paragraph that contains a citation marker but does not include the quote in prose. "
        '[citation: notes.txt - "verbatim phrase from notes"] '
        "The rest of the paragraph continues without that phrase."
    )
    issues = sg._compute_style_issues(content)
    msg = " ".join(issues)
    assert "Citation quote not present" in msg
    assert "Do NOT add quotation marks" in msg


def test_style_gate_flags_uncited_factual_sentence_when_other_citations_exist():
    sg = ChapterSubgraph(config=SubgraphConfig())
    content = (
        'verbatim phrase from source [citation: notes.txt - "verbatim phrase from source"]. '
        "About 50% of the time, this happens."
    )
    issues = sg._compute_style_issues(content)
    assert any("claim-level grounding" in i for i in issues)


