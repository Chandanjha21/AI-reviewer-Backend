#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

exec venv/bin/celery \
  -A app.tasks.celery_app.celery_app \
  worker \
  --loglevel=info \
  --queues=work_item_processing_queue
