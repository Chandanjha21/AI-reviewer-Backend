import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


logger = logging.getLogger(__name__)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        print(exc)
        logger.exception("Unhandled request error")
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"},
        )
