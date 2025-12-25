#!/usr/bin/env python3
"""
Audit a workflow run for:
- placeholder usage
- LLM provider fallback usage (Anthropic -> OpenAI)

This doesn't regenerate anything; it only inspects DB + saved conversation logs.

Usage:
  cd ghostline/api
  poetry run python scripts/audit_run_integrity.py --task-id <uuid>
  poetry run python scripts/audit_run_integrity.py --latest
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Optional


PLACEHOLDER_MARKERS = [
    "[This is placeholder content - real content requires API keys]",
    "This chapter explores the key concepts and ideas related to the topic at hand.",
    "A compelling exploration of the subject matter.",
]


def _find_conversation_logs_for_workflow(workflow_id: str, base_dir: Path) -> list[Path]:
    if not workflow_id:
        return []
    if not base_dir.exists():
        return []
    hits: list[Path] = []
    for p in base_dir.glob("*.json"):
        if workflow_id in p.name:
            hits.append(p)
    return sorted(hits)


def _scan_logs_for_fallback(log_paths: list[Path]) -> dict[str, Any]:
    fallback_lines = []
    models_used = set()
    for p in log_paths:
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        for m in data.get("messages", []) or []:
            content = (m.get("content") or "").lower()
            model = (m.get("model") or "").strip()
            if model:
                models_used.add(model)
            if "falling back to openai model" in content:
                fallback_lines.append(
                    {
                        "file": str(p),
                        "timestamp": m.get("timestamp"),
                        "agent": m.get("agent"),
                        "content_preview": (m.get("content") or "")[:220],
                    }
                )
    return {
        "fallback_used": len(fallback_lines) > 0,
        "fallback_events": fallback_lines,
        "models_used": sorted(models_used),
    }


def _scan_workflow_state_for_placeholders(workflow_state: dict) -> dict[str, Any]:
    findings = []

    outline = workflow_state.get("outline") or {}
    outline_json = json.dumps(outline, default=str)
    for marker in PLACEHOLDER_MARKERS:
        if marker in outline_json:
            findings.append({"where": "outline", "marker": marker})

    for ch in workflow_state.get("chapters", []) or []:
        content = (ch.get("content") or "")
        for marker in PLACEHOLDER_MARKERS:
            if marker in content:
                findings.append({"where": f"chapter_{ch.get('number')}", "marker": marker})

    return {
        "placeholders_used": len(findings) > 0,
        "placeholder_findings": findings,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--task-id", required=False)
    ap.add_argument("--latest", action="store_true")
    ap.add_argument("--log-dir", default="logs/conversations")
    args = ap.parse_args()

    from sqlalchemy import desc
    from app.db.base import SessionLocal
    from app.models.generation_task import GenerationTask, TaskStatus, TaskType

    db = SessionLocal()
    try:
        task: Optional[GenerationTask] = None
        if args.task_id:
            task = db.query(GenerationTask).filter(GenerationTask.id == args.task_id).first()
        elif args.latest:
            task = (
                db.query(GenerationTask)
                .filter(GenerationTask.task_type == TaskType.CHAPTER_GENERATION)
                .filter(GenerationTask.status == TaskStatus.COMPLETED)
                .order_by(desc(GenerationTask.created_at))
                .first()
            )
        else:
            raise SystemExit("Provide --task-id or --latest")

        if not task:
            raise SystemExit("Task not found")

        output = task.output_data or {}
        wf = (output.get("workflow_state") or {}) if isinstance(output, dict) else {}
        workflow_id = str(wf.get("workflow_id") or "")

        log_dir = Path(args.log_dir)
        log_paths = _find_conversation_logs_for_workflow(workflow_id, log_dir)

        placeholder_report = _scan_workflow_state_for_placeholders(wf)
        fallback_report = _scan_logs_for_fallback(log_paths)

        report = {
            "task_id": str(task.id),
            "workflow_id": workflow_id,
            "strict_mode_env": None,  # best-effort: env not persisted
            "placeholders": placeholder_report,
            "fallback": fallback_report,
            "conversation_logs": [str(p) for p in log_paths],
        }

        print("=== RUN INTEGRITY AUDIT ===")
        print(f"task_id: {report['task_id']}")
        print(f"workflow_id: {report['workflow_id']}")
        print(f"placeholders_used: {placeholder_report['placeholders_used']}")
        print(f"fallback_used: {fallback_report['fallback_used']}")
        if fallback_report["models_used"]:
            print(f"models_used: {', '.join(fallback_report['models_used'][:10])}" + (" ..." if len(fallback_report["models_used"]) > 10 else ""))

        if placeholder_report["placeholders_used"]:
            print("\nPlaceholder findings:")
            for f in placeholder_report["placeholder_findings"]:
                print(f"- {f['where']}: {f['marker']}")

        if fallback_report["fallback_used"]:
            print("\nFallback events:")
            for e in fallback_report["fallback_events"][:10]:
                print(f"- {e['timestamp']} {e['agent']}: {e['content_preview']}")

        # Write JSON report next to logs
        out_path = Path("logs") / f"run_integrity_{task.id}.json"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"\nSaved: {out_path}")
    finally:
        db.close()


if __name__ == "__main__":
    main()


