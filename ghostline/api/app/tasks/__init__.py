"""
Celery tasks for async AI generation.

These tasks are queued and executed by Celery workers.
"""

from app.tasks.generation import (
    generate_book_task,
    generate_chapter_task,
    generate_outline_task,
    analyze_voice_task,
)

__all__ = [
    "generate_book_task",
    "generate_chapter_task", 
    "generate_outline_task",
    "analyze_voice_task",
]

