from pathlib import Path

from evals.run import evaluate_case


def test_eval_harness_smoke_case_runs_and_verifies_quotes():
    api_dir = Path(__file__).resolve().parents[2]  # ghostline/api
    case_dir = api_dir / "evals" / "cases" / "smoke_case"

    reports = evaluate_case(case_dir, enable_vlm=False)
    assert len(reports) == 1
    report = reports[0]

    citation = report["citation_report"]
    assert citation["inline_invalid_format"] == 0
    assert citation["inline_unverified"] == 0
    assert citation["inline_quality"] == 1.0


