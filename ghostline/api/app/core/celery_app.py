"""
Celery configuration for background tasks.
"""

from celery import Celery

from app.core.config import settings

# Create Celery instance
celery_app = Celery(
    "ghostline",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.tasks"],
)

# Configure Celery
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    # Task routing
    task_routes={
        "app.tasks.process_source_material": {"queue": "processing"},
        "app.tasks.generate_chapter": {"queue": "generation"},
        "app.tasks.analyze_voice": {"queue": "analysis"},
    },
    # Task time limits
    task_time_limit=3600,  # 1 hour hard limit
    task_soft_time_limit=3000,  # 50 minutes soft limit
    # Result backend settings
    result_expires=86400,  # Results expire after 24 hours
    # Worker settings
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
)
