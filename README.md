# AI Email Review Backend

FastAPI backend for organization-scoped AI email draft review with Supabase, custom JWT auth, OpenAI draft generation, Celery, and Redis.

## Setup

```bash
cd Backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Fill `.env` with Supabase, JWT, OpenAI, and Redis values.

Run `migrations/001_initial_schema.sql` in the Supabase SQL editor before starting the API.

## Run

```bash
cd Backend
uvicorn main:app --reload
```

Start Redis separately, then run the Celery worker:

```bash
cd Backend
./scripts/start_work_item_worker.sh
```

If you start Celery manually, the worker must consume `work_item_processing_queue`:

```bash
cd Backend
venv/bin/celery -A app.tasks.celery_app.celery_app worker --loglevel=info --queues=work_item_processing_queue
```

## Main Flow

1. `POST /auth/register-organization` creates an organization and first admin.
2. `POST /auth/login` returns a bearer token.
3. Admin creates reviewers with `POST /users`.
4. Admin or reviewer creates a lead/customer with `POST /customers`.
5. A work item is created and queued for OpenAI draft generation.
6. Reviewer/admin edits, approves, rejects, regenerates, or admin reassigns from `/work-items`.
