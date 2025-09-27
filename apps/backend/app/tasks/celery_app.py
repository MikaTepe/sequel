import os
from celery import Celery
from celery.schedules import crontab
from kombu import Queue

from ..core.config import get_settings

settings = get_settings()

# Create Celery instance
celery_app = Celery("sequel")

# Configuration
celery_app.conf.update(
    # Broker settings
    broker_url=settings.celery_broker_url,
    result_backend=settings.celery_result_backend,

    # Task settings
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,

    # Task routing
    task_routes={
        'app.tasks.nlp.keybert_tasks.extract_keywords_async': {'queue': 'keybert'},
        'app.tasks.nlp.keybert_tasks.extract_keywords_batch_async': {'queue': 'keybert_batch'},
        'app.tasks.nlp.keybert_tasks.keybert_health_check': {'queue': 'monitoring'},
    },

    # Queue definitions
    task_default_queue='default',
    task_queues=(
        Queue('default', routing_key='default'),
        Queue('keybert', routing_key='keybert'),
        Queue('keybert_batch', routing_key='keybert_batch'),
        Queue('monitoring', routing_key='monitoring'),
    ),

    # Task execution settings
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes

    # Result settings
    result_expires=3600,  # 1 hour
    result_persistent=True,

    # Worker settings
    worker_log_format='[%(asctime)s: %(levelname)s/%(processName)s] %(message)s',
    worker_task_log_format='[%(asctime)s: %(levelname)s/%(processName)s][%(task_name)s(%(task_id)s)] %(message)s',

    # Monitoring
    worker_send_task_events=True,
    task_send_sent_event=True,

    # Beat schedule for periodic tasks
    beat_schedule={
        'keybert-health-check': {
            'task': 'app.tasks.nlp.keybert_tasks.keybert_health_check',
            'schedule': crontab(minute='*/15'),  # Every 15 minutes
            'options': {'queue': 'monitoring'}
        },
        # Add more periodic tasks here
    },
)

# Auto-discover tasks
celery_app.autodiscover_tasks([
    'app.tasks.nlp',
    # Add other task modules here
])


# Task error handling
@celery_app.task(bind=True)
def debug_task(self):
    """Debug task for testing Celery setup"""
    print(f'Request: {self.request!r}')
    return 'Debug task completed'


# Task failure handler
@celery_app.task(bind=True)
def handle_task_failure(self, task_id, error, traceback):
    """Handle task failures"""
    print(f'Task {task_id} failed: {error}')
    # Here you could send notifications, log to external systems, etc.


# Celery signals
from celery.signals import (
    task_prerun,
    task_postrun,
    task_failure,
    worker_ready,
    worker_shutdown
)
import logging

logger = logging.getLogger(__name__)


@task_prerun.connect
def task_prerun_handler(sender=None, task_id=None, task=None, args=None, kwargs=None, **kwds):
    """Called before task execution"""
    logger.info(f'Task {task_id} ({task.name}) started')


@task_postrun.connect
def task_postrun_handler(sender=None, task_id=None, task=None, args=None, kwargs=None, retval=None, state=None, **kwds):
    """Called after task execution"""
    logger.info(f'Task {task_id} ({task.name}) finished with state: {state}')


@task_failure.connect
def task_failure_handler(sender=None, task_id=None, exception=None, traceback=None, einfo=None, **kwds):
    """Called when task fails"""
    logger.error(f'Task {task_id} failed: {exception}', exc_info=einfo)


@worker_ready.connect
def worker_ready_handler(sender=None, **kwargs):
    """Called when worker is ready"""
    logger.info(f'Worker {sender.hostname} is ready')


@worker_shutdown.connect
def worker_shutdown_handler(sender=None, **kwargs):
    """Called when worker shuts down"""
    logger.info(f'Worker {sender.hostname} is shutting down')


# Development helper
if __name__ == '__main__':
    celery_app.start()