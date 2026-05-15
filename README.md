# AI Sales Workbench - Backend

A robust, production-ready FastAPI backend for the AI Sales Workbench. This system provides an organization-scoped platform for generating, reviewing, and managing AI-crafted email drafts for sales leads using OpenAI, Supabase, Celery, and Redis.

## 🌟 Key Features

- **Multi-Tenant Architecture**: Organization-scoped data access, ensuring strict isolation between different companies.
- **Custom JWT Authentication**: Secure login and session management with role-based access control (Admin vs. Reviewer).
- **Asynchronous AI Processing**: Offloads heavy OpenAI draft generation tasks to background workers using Celery and Redis.
- **Complete Review Workflow**: Enables reviewers to approve, edit, reject, or regenerate AI-generated email drafts before they are sent.
- **Robust Database**: Integrated with Supabase (PostgreSQL) for scalable and reliable data storage.

## 🛠️ Technology Stack

- **Framework**: [FastAPI](https://fastapi.tiangolo.com/) - High performance, easy to learn, fast to code, ready for production.
- **Database**: [Supabase](https://supabase.com/) (PostgreSQL)
- **Task Queue**: [Celery](https://docs.celeryq.dev/)
- **Message Broker**: [Redis](https://redis.io/)
- **AI Integration**: [OpenAI API](https://openai.com/)
- **Authentication**: Custom JWT (JSON Web Tokens)

## 🚀 Local Setup & Installation

Follow these steps to get the backend running on your local machine.

### Prerequisites

1. **Python 3.10+**: Ensure Python is installed.
2. **Redis**: Must be installed and running locally (or have a remote Redis URL).
3. **Supabase Project**: Create a project on Supabase and have your database credentials ready.
4. **OpenAI API Key**: Required for AI draft generation.

### 1. Clone & Environment Setup

```bash
# Navigate to the backend directory
cd AI-reviewer-Backend

# Create a virtual environment
python -m venv .venv

# Activate the virtual environment
# On macOS/Linux:
source .venv/bin/activate
# On Windows:
# .venv\Scripts\activate

# Install the required dependencies
pip install -r requirements.txt
```

### 2. Configuration

Copy the example environment file and configure your variables:

```bash
cp .env.example .env
```

Open the `.env` file and fill in your specific values:
- `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` from your Supabase dashboard.
- `JWT_SECRET_KEY` (generate a secure random string).
- `OPENAI_API_KEY` for AI features.
- `REDIS_URL` (usually `redis://localhost:6379/0` if running locally).

you can find the total list of enviornment variables to use in the `.env.example` file copy that in your `.env` and update it with specific values for yourself

### 3. Database Migration

Before starting the API, you need to set up the database schema.
Go to your Supabase SQL editor and run the contents of the migration file:
`migrations/001_initial_schema.sql`

### 4. Running the Application

You will need to run the FastAPI server and the Celery worker concurrently.

**Terminal 1: Start the FastAPI Server**
```bash
# From the root of the backend directory (with virtual env activated)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
The API will be available at `http://localhost:8000`.
You can access the interactive Swagger documentation at `http://localhost:8000/docs`.

**Terminal 2: Start Redis (if not running as a service)**
```bash
redis-server
```

**Terminal 3: Start the Celery Worker**
```bash
# Make the script executable first (macOS/Linux)
chmod +x scripts/start_work_item_worker.sh

# Run the worker
./scripts/start_work_item_worker.sh
```

*(Alternative manual start for Celery)*:
```bash
celery -A app.tasks.celery_app.celery_app worker --loglevel=info --queues=work_item_processing_queue
```

## 📖 Main Workflow

1. **Organization Onboarding**: Call `POST /auth/register-organization` to create a new organization and its initial admin user.
2. **Authentication**: Use `POST /auth/login` to authenticate and receive a Bearer JWT token. Include this token in the `Authorization` header for subsequent requests.
3. **User Management**: Admins can invite or create new reviewers via `POST /users`.
4. **Lead Creation**: Users (Admins/Reviewers) can add new sales leads/customers via `POST /customers`.
5. **AI Generation**: Upon lead creation, a work item is automatically generated and queued for the Celery worker to generate an email draft using OpenAI.
6. **Review Process**: Reviewers use the `/work-items` endpoints to fetch pending drafts, edit the content, and either approve, reject, or request regeneration.

## 🗂️ Project Structure

```text
app/
├── auth/           # Authentication and registration logic
├── config/         # Environment variables and app settings
├── core/           # Security, dependencies, and error handling
├── customers/      # Lead/Customer management
├── helpers/        # Database and utility helpers
├── organisations/  # Organization tenant logic
├── services/       # Core business logic (OpenAI integration, etc.)
├── tasks/          # Celery app and asynchronous tasks
├── users/          # User management
├── work_items/     # Review workflow logic
└── main.py         # FastAPI application entry point
```
