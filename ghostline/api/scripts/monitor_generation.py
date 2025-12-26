#!/usr/bin/env python
"""
Real-time progress monitor for book generation.
Shows a live updating progress bar and status.
"""
import os
import sys
import time
from datetime import datetime

# Add paths
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import func
from app.db.base import SessionLocal
from app.models.generation_task import GenerationTask, TaskStatus
from app.models.llm_usage_log import LLMUsageLog


def progress_bar(progress: int, width: int = 40) -> str:
    """Create a text progress bar."""
    filled = int(width * progress / 100)
    bar = "█" * filled + "░" * (width - filled)
    return f"[{bar}] {progress}%"


def monitor_task(task_id: str = None, interval: int = 2):
    """Monitor a specific task or the latest running task."""
    print("\n" + "=" * 70)
    print("📊 GHOSTLINE GENERATION MONITOR")
    print("=" * 70)
    
    last_step = None
    last_log_count = 0
    start_time = datetime.now()
    
    while True:
        db = SessionLocal()
        try:
            # Find task
            if task_id:
                task = db.query(GenerationTask).filter(GenerationTask.id == task_id).first()
            else:
                task = db.query(GenerationTask).filter(
                    GenerationTask.status.in_([TaskStatus.RUNNING, TaskStatus.QUEUED, TaskStatus.PAUSED])
                ).order_by(GenerationTask.created_at.desc()).first()
            
            if not task:
                print("No active tasks found. Waiting...")
                time.sleep(interval)
                continue
            
            # Get LLM usage stats
            log_count = db.query(func.count(LLMUsageLog.id)).filter(
                LLMUsageLog.project_id == task.project_id
            ).scalar() or 0
            
            total_cost = db.query(func.sum(LLMUsageLog.total_cost)).filter(
                LLMUsageLog.project_id == task.project_id
            ).scalar() or 0
            
            total_tokens = db.query(func.sum(LLMUsageLog.total_tokens)).filter(
                LLMUsageLog.project_id == task.project_id
            ).scalar() or 0
            
            # Clear line and print status
            elapsed = (datetime.now() - start_time).total_seconds()
            
            # Print update if changed
            if task.current_step != last_step or log_count != last_log_count:
                timestamp = datetime.now().strftime("%H:%M:%S")
                print(f"\n[{timestamp}] {task.status.value.upper()}")
                print(progress_bar(task.progress))
                print(f"Step: {task.current_step}")
                print(f"💰 Cost: ${total_cost:.4f} | 🔢 Tokens: {total_tokens:,} | 📞 API Calls: {log_count}")
                
                # Show chapters if available
                if task.output_data:
                    ws = task.output_data.get('workflow_state', {})
                    chapters = ws.get('chapters', [])
                    if chapters:
                        print(f"📚 Chapters: {len(chapters)}")
                        for ch in chapters[-2:]:  # Last 2 chapters
                            print(f"   - Ch{ch.get('number')}: {ch.get('title', 'Untitled')[:40]} ({ch.get('word_count', 0)} words)")
                
                last_step = task.current_step
                last_log_count = log_count
            else:
                # Just show a dot to indicate we're still monitoring
                print(".", end="", flush=True)
            
            # Check for completion
            if task.status.value in ['COMPLETED', 'FAILED', 'CANCELLED']:
                print("\n" + "=" * 70)
                print(f"🏁 FINAL: {task.status.value}")
                print(f"   Duration: {elapsed:.1f}s")
                print(f"   Total Cost: ${total_cost:.4f}")
                print(f"   Total Tokens: {total_tokens:,}")
                
                if task.output_data:
                    ws = task.output_data.get('workflow_state', {})
                    chapters = ws.get('chapters', [])
                    total_words = sum(ch.get('word_count', 0) for ch in chapters)
                    print(f"   Chapters: {len(chapters)}")
                    print(f"   Total Words: {total_words:,}")
                print("=" * 70)
                break
                
        finally:
            db.close()
        
        time.sleep(interval)


if __name__ == "__main__":
    task_id = sys.argv[1] if len(sys.argv) > 1 else None
    monitor_task(task_id)

