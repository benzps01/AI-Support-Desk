import os
from celery import Celery
from app.config import settings

# Initialize Celery app Instance
# 'worker' is the name of our main celery app instance

celery_app = Celery(
    "worker",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["worker.tasks"]
)

# Optional Config
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,  # to keep track of task failures while silent executions
)

if __name__ == "__main__":
    celery_app.start()