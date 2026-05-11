import structlog
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.core.config import settings
from app.core.exceptions import AppException
from app.core.middleware import CorrelationIDMiddleware
from app.api.v1 import auth, events, dashboards, alerts, websocket, reports

# ─── Structured Logging ─────────────────────────
structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.dev.ConsoleRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(0),
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=True,
)
log = structlog.get_logger()

# ─── Rate Limiter ────────────────────────────────
limiter = Limiter(key_func=get_remote_address, default_limits=["200/minute"])


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("app_startup", app=settings.APP_NAME, debug=settings.DEBUG)

    # Auto-create tables on startup
    from app.db.session import engine, Base
    from app.models import __all__  # noqa: F401 — ensure all models are imported
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    log.info("database_tables_created")

    yield
    log.info("app_shutdown", app=settings.APP_NAME)


app = FastAPI(
    title=settings.APP_NAME,
    description="Real-Time Analytics & Reporting Platform — Production-grade SaaS analytics tool",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Attach limiter to app state
app.state.limiter = limiter

# ─── Middleware (order matters: last added = first executed) ──
app.add_middleware(CorrelationIDMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Exception Handlers ─────────────────────────
@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """Centralized handler for all custom application exceptions."""
    correlation_id = getattr(request.state, "correlation_id", "unknown")
    log.warning(
        "app_exception",
        error_code=exc.error_code,
        message=exc.message,
        status_code=exc.status_code,
        correlation_id=correlation_id,
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.error_code,
                "message": exc.message,
                "details": exc.details,
                "correlation_id": correlation_id,
            }
        },
    )


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    correlation_id = getattr(request.state, "correlation_id", "unknown")
    return JSONResponse(
        status_code=429,
        content={
            "error": {
                "code": "RATE_LIMITED",
                "message": "Too many requests. Please slow down.",
                "details": {"retry_after": str(exc.detail)},
                "correlation_id": correlation_id,
            }
        },
    )


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
    return JSONResponse(
        status_code=400,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": str(exc),
                "details": {},
            }
        },
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    correlation_id = getattr(request.state, "correlation_id", "unknown")
    log.error("unhandled_exception", error=str(exc), exc_info=True, correlation_id=correlation_id)
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred",
                "details": {},
                "correlation_id": correlation_id,
            }
        },
    )


# ─── Routes ─────────────────────────────────────
app.include_router(auth.router, prefix=settings.API_V1_PREFIX)
app.include_router(events.router, prefix=settings.API_V1_PREFIX)
app.include_router(dashboards.router, prefix=settings.API_V1_PREFIX)
app.include_router(alerts.router, prefix=settings.API_V1_PREFIX)
app.include_router(websocket.router, prefix=settings.API_V1_PREFIX)
app.include_router(reports.router, prefix=settings.API_V1_PREFIX)


@app.get("/health", tags=["Infrastructure"])
async def health():
    """Health check endpoint for load balancers and monitoring."""
    return {"status": "healthy", "service": settings.APP_NAME, "version": "1.0.0"}


@app.get("/", tags=["Infrastructure"])
async def root():
    return {
        "name": settings.APP_NAME,
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
        "metrics": "/metrics",
    }


@app.get("/metrics", tags=["Infrastructure"])
async def metrics():
    """Prometheus-compatible metrics endpoint for observability.

    Exposes key application metrics: uptime, active WebSocket connections,
    registered routes, and system info.
    """
    import time
    from app.api.v1.websocket import manager

    return {
        "service": settings.APP_NAME,
        "version": "1.0.0",
        "uptime_seconds": round(time.time() - _app_start_time, 2),
        "websocket_connections": manager.connection_count,
        "websocket_orgs": len(manager.active),
        "registered_routes": len(app.routes),
        "python_version": "3.13",
        "framework": "FastAPI",
        "database": "PostgreSQL + SQLAlchemy 2.0 async",
        "task_queue": "Celery + Redis",
        "cache": "Redis",
    }


# Track app start time for uptime metric
import time as _time
_app_start_time = _time.time()
