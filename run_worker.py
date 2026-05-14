# run_worker.py
import os
import subprocess
import threading
from fastapi import FastAPI
import uvicorn

app = FastAPI()

@app.get("/")
@app.get("/health")
def health_check():
    """Tells Render's load balancer that this instance is alive."""
    return {"status": "worker_running"}

def run_celery_worker():
    """Runs the worker process. Drops concurrency to 1 to stay under 512MB RAM."""
    # Ensure current directory is in Python's lookup path
    env = os.environ.copy()
    env["PYTHONPATH"] = f".:{env.get('PYTHONPATH', '')}"

    cmd = [
        "celery", 
        "-A", "app.tasks.celery_app.celery_app",  # Pointing to: file_path.variable_name
        "worker", 
        "--loglevel=info", 
        "--concurrency=1",
        "--pool=solo"
    ]
    subprocess.run(cmd, env=env)


if __name__ == "__main__":
    # 1. Start Celery in the background
    threading.Thread(target=run_celery_worker, daemon=True).start()
    
    # 2. Bind the main thread to Render's required $PORT
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
