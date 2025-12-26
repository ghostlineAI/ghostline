from orchestrator.workflow import _build_chapter_canon, _format_chapter_canon


def test_build_and_format_chapter_canon_prefers_grounded_claims():
    canon = _build_chapter_canon(
        chapter_number=1,
        title="Test Chapter",
        chapter_outline={"summary": "Outline intent", "key_points": ["A", "B"]},
        chapter_result={
            "claim_mappings": [
                {"claim": "Supported claim", "is_supported": True, "confidence": 0.9},
                {"claim": "Needs review claim", "is_supported": True, "needs_human_review": True},
                {"claim": "Unsupported claim", "is_supported": False},
            ],
            "quality_gate_report": {"citations_ok": True, "style_issues": ["Too many headers"]},
        },
    )

    assert canon["chapter_number"] == 1
    assert canon["title"] == "Test Chapter"
    assert canon["outline_summary"] == "Outline intent"
    assert canon["key_points"] == ["A", "B"]
    assert "Supported claim" in canon["grounded_commitments"]
    assert "Needs review claim" in canon["needs_review"]
    assert "Unsupported claim" in canon["unsupported"]

    text = _format_chapter_canon(canon)
    assert "CHAPTER 1" in text
    assert "Grounded commitments:" in text
    assert "- Supported claim" in text
    assert "Needs review" in text


