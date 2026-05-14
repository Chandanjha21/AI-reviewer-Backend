import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.auth.routes import router as auth_router
from app.config.settings import settings
from app.core.errors import register_exception_handlers
from app.customers.routes import router as customers_router
from app.helpers.db_helper import init_db
from app.users.routes import router as users_router
from app.work_items.routes import router as work_items_router


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        logger.info("Starting application lifespan")
        init_db()
        yield
    except Exception as e:
        print(e)
        logger.exception("Application startup failed")
        raise
    finally:
        logger.info("Application shutdown complete")


def register_middleware(app: FastAPI) -> None:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


def register_routes(app: FastAPI) -> None:
    app.include_router(auth_router)
    app.include_router(users_router)
    app.include_router(customers_router)
    app.include_router(work_items_router)

    @app.get("/health", tags=["health"])
    def health():
        return {"status": "ok"}


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        lifespan=lifespan,
    )

    register_middleware(app)
    register_exception_handlers(app)
    register_routes(app)

    return app


app = create_app()
