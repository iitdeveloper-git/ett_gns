#!/bin/bash

echo "Starting Celery Worker..."
celery -A ett_gns_app.tasks.celery_app worker --loglevel=INFO --queues=notifications.default --concurrency=2 &

echo "Starting Celery Beat Scheduler..."
celery -A ett_gns_app.tasks.celery_app beat --loglevel=INFO --schedule=/tmp/celerybeat-schedule &

echo "Starting Outbox Publisher..."
python3 -m ett_gns_app.cli outbox &

echo "Running Database Migrations..."
alembic upgrade head

echo "Starting FastAPI Server..."
exec uvicorn ett_gns_app.main:app --host 0.0.0.0 --port ${PORT:-5000} --proxy-headers
