#!/usr/bin/env python3
"""
End-to-end sanity test for *automatic* cost logging.

This verifies that:
- Chat (agent) calls are recorded to `llm_usage_logs`
- Embedding calls are recorded (call_type=embedding)
- Vision calls are recorded when VLM is used (call_type=vision)

It creates a temporary GenerationTask, sets cost context, performs a few calls,
asserts logs exist, and then cleans up.
"""

import sys
from pathlib import Path

# Ensure `app.*` imports work when running from repo root
sys.path.insert(0, str(Path(__file__).parent.parent))

# Ensure `agents.*` imports work (repo layout: ghostline/agents/agents/...)
AGENTS_PATH = Path(__file__).resolve().parents[2] / "agents"
if str(AGENTS_PATH) not in sys.path:
    sys.path.insert(0, str(AGENTS_PATH))


def main() -> int:
    from sqlalchemy import func

    from app.db.base import SessionLocal
    from app.models.generation_task import GenerationTask, TaskStatus, TaskType
    from app.models.llm_usage_log import LLMUsageLog
    from app.models.project import Project

    from agents.base.agent import set_cost_context, clear_cost_context
    from agents.specialized.content_drafter import ContentDrafterAgent

    from app.services.embeddings import get_embedding_service
    from app.services.document_processor import DocumentProcessor

    # Repo root is 3 levels up from `ghostline/api/scripts/`
    IMAGE_PATH = str(Path(__file__).resolve().parents[3] / "mental_health.png")

    db = SessionLocal()
    try:
        project = db.query(Project).filter(Project.title == "Mental Health Guide").first()
        if not project:
            print("❌ Missing project 'Mental Health Guide' (needed for test).")
            return 1

        # Create an ephemeral task so we can filter logs precisely
        task = GenerationTask(
            project_id=project.id,
            task_type=TaskType.CHAPTER_GENERATION,
            status=TaskStatus.RUNNING,
            current_step="cost_logging_test",
            progress=0,
            input_data={"test": True},
        )
        db.add(task)
        db.commit()
        db.refresh(task)

        workflow_run_id = f"cost_logging_test_{task.id}"
        token = set_cost_context(
            project_id=project.id,
            task_id=task.id,
            workflow_run_id=workflow_run_id,
            db_session=db,
        )

        before = db.query(func.count(LLMUsageLog.id)).filter(LLMUsageLog.task_id == task.id).scalar() or 0

        # 1) Agent (chat) call
        drafter = ContentDrafterAgent()
        _ = drafter.invoke("Reply with the single word: ok")

        # 2) Embedding call (OpenAI or local fallback)
        emb = get_embedding_service()
        _ = emb.embed_text("hello world")

        # 3) Vision call (Claude vision) if available
        dp = DocumentProcessor()
        _ = dp._extract_with_vlm(IMAGE_PATH)

        clear_cost_context(token)

        after = db.query(func.count(LLMUsageLog.id)).filter(LLMUsageLog.task_id == task.id).scalar() or 0
        logs = (
            db.query(LLMUsageLog)
            .filter(LLMUsageLog.task_id == task.id)
            .order_by(LLMUsageLog.created_at.asc())
            .all()
        )

        print("\n=== COST LOGGING TEST RESULTS ===")
        print(f"task_id={task.id}")
        print(f"logs_before={before} logs_after={after} new_logs={after - before}")

        by_type = {}
        for log in logs:
            by_type.setdefault(log.call_type or "unknown", 0)
            by_type[log.call_type or "unknown"] += 1

        print("by_call_type:", by_type)

        # Assertions (minimum expectations)
        if by_type.get("chat", 0) < 1:
            raise AssertionError("Expected at least 1 chat log")
        if by_type.get("embedding", 0) < 1:
            raise AssertionError("Expected at least 1 embedding log")
        if by_type.get("vision", 0) < 1:
            raise AssertionError("Expected at least 1 vision log")

        total_cost = sum(float(l.total_cost or 0.0) for l in logs)
        total_tokens = sum(int(l.total_tokens or 0) for l in logs)
        print(f"total_tokens={total_tokens} total_cost=${total_cost:.6f}")

        # Show a few rows
        for l in logs[:10]:
            print(
                f"- {l.call_type} {l.provider}/{l.model} agent={l.agent_name} "
                f"in={l.input_tokens} out={l.output_tokens} cost=${l.total_cost:.6f} "
                f"dur_ms={l.duration_ms}"
            )

        print("✅ PASS: automatic cost logging recorded chat + embedding + vision calls.")
        return 0

    finally:
        # Best-effort cleanup
        try:
            if "task" in locals():
                # Delete logs for this task
                for log in (
                    db.query(LLMUsageLog).filter(LLMUsageLog.task_id == task.id).all()
                ):
                    db.delete(log)
                db.delete(task)
                db.commit()
        except Exception:
            try:
                db.rollback()
            except Exception:
                pass
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())


