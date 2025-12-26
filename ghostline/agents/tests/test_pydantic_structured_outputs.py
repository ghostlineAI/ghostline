from agents.specialized.schemas import (
    BookOutlineModel,
    CohesionResultModel,
    FactCheckResultModel,
)


def test_outline_schema_validation_smoke():
    m = BookOutlineModel.model_validate(
        {
            "title": "T",
            "premise": "P",
            "chapters": [{"number": 1, "title": "C1", "summary": "S", "key_points": []}],
            "themes": [],
            "target_audience": "A",
        }
    )
    assert m.chapters[0].number == 1


def test_fact_schema_validation_smoke():
    m = FactCheckResultModel.model_validate(
        {
            "accuracy_score": 0.8,
            "claim_mappings": [
                {
                    "claim": "X",
                    "source_citation": None,
                    "source_quote": None,
                    "verification_status": "UNSUPPORTED",
                    "is_supported": False,
                    "confidence": 0.2,
                    "needs_human_review": True,
                    "notes": "",
                }
            ],
            "findings": [
                {
                    "type": "unsupported",
                    "severity": "high",
                    "location": "p1",
                    "issue": "bad",
                    "suggestion": "remove",
                }
            ],
            "unsupported_claims": ["X"],
            "low_confidence_citations": [],
            "summary": "s",
        }
    )
    assert m.findings[0].severity == "high"


def test_cohesion_schema_validation_smoke():
    m = CohesionResultModel.model_validate(
        {
            "cohesion_score": 0.7,
            "issues": [
                {
                    "type": "transition",
                    "location": "middle",
                    "description": "abrupt",
                    "severity": "medium",
                    "suggestion": "add bridge",
                }
            ],
            "strengths": ["good opening"],
            "summary": "ok",
        }
    )
    assert m.issues[0].type == "transition"


