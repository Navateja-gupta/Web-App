import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.errors import AppError
from app.services.email_sender import OutboxWorker

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("app")


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    worker = None
    if settings.EMAIL_ENABLED and settings.EMAIL_WORKER_ENABLED:
        if settings.email_configured:
            worker = OutboxWorker(settings.EMAIL_POLL_SECONDS)
            worker.start()
        else:
            logger.warning("EMAIL_ENABLED is true but SMTP_USERNAME/SMTP_PASSWORD are missing; emails will wait in the outbox.")
    try:
        yield
    finally:
        if worker is not None:
            worker.stop()


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version="1.1.0",
        lifespan=lifespan,
        openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # Explicit origins (not "*") are required because auth cookies are sent with credentials.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )

    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        headers = {"WWW-Authenticate": "Bearer"} if exc.status_code == 401 else None
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail}, headers=headers)

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        # Full details go to the server log; the client gets a safe generic message.
        logger.exception("Unhandled error on %s %s", request.method, request.url.path)
        return JSONResponse(status_code=500, content={"detail": "Internal server error"})

    @app.middleware("http")
    async def security_headers(request: Request, call_next):  # type: ignore[no-untyped-def]
        response = await call_next(request)
        # Browsers must not guess content types (uploaded files are served as what they are).
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    app.include_router(api_router, prefix=settings.API_V1_PREFIX)

    # Local media (vendor portfolio images). Replace with object storage/CDN in the cloud.
    settings.MEDIA_ROOT.mkdir(parents=True, exist_ok=True)
    app.mount(settings.MEDIA_URL_PATH, StaticFiles(directory=settings.MEDIA_ROOT), name="media")
    return app


app = create_app()
