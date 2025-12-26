from orchestrator.subgraphs import ChapterSubgraph, SubgraphConfig


def test_format_fact_feedback_uses_findings_and_unsupported_claims():
    sg = ChapterSubgraph(config=SubgraphConfig())
    structured = {
        "summary": "Overall, several claims are not grounded.",
        "findings": [
            {
                "type": "unsupported",
                "severity": "high",
                "location": "Paragraph 2",
                "issue": "A quote is attributed to the author but does not exist in sources.",
                "suggestion": "Remove the quote or replace with a verified source quote.",
            },
            {
                "type": "low_confidence",
                "severity": "low",
                "location": "Paragraph 5",
                "issue": "Paraphrase may be too strong.",
                "suggestion": "Soften the claim and add a supporting citation.",
            },
        ],
        "unsupported_claims": [
            "The author was diagnosed at age 12.",
            "Meditation cured the condition.",
        ],
        "low_confidence_citations": ["A paraphrased claim with weak support."],
    }

    out = sg._format_fact_feedback(structured)
    assert "Summary:" in out
    assert "Top issues:" in out
    assert "Unsupported claims:" in out
    assert "Low-confidence citations:" in out
    # High-severity issue should be present
    assert "(high)" in out
    assert "does not exist in sources" in out


def test_format_cohesion_feedback_uses_summary_and_top_issues():
    sg = ChapterSubgraph(config=SubgraphConfig())
    structured = {
        "summary": "Flow is choppy with abrupt topic shifts.",
        "issues": [
            {
                "type": "transition",
                "location": "Between sections 1 and 2",
                "description": "Abrupt shift without a bridge sentence.",
                "severity": "high",
                "suggestion": "Add a short transition that links the two ideas.",
            },
            {
                "type": "pacing",
                "location": "Ending",
                "description": "Conclusion is too short.",
                "severity": "medium",
                "suggestion": "Expand with a closing reflection.",
            },
        ],
    }

    out = sg._format_cohesion_feedback(structured)
    assert "Summary:" in out
    assert "Top issues:" in out
    assert "(high)" in out
    assert "Abrupt shift" in out


