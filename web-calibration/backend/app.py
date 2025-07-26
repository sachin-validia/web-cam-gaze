"""
Main FastAPI application for web-based calibration system
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
import structlog
import sys

# Relative imports succeed because 'backend' is a package
from .api import calibration, screen, session  # noqa: F401
from .db.database import init_db, close_db  # noqa: F401
from .utils.config import settings  # noqa: F401

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer(),
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle startup and shutdown events"""
    # Startup
    logger.info("Starting calibration API server")
    init_db()
    yield
    # Shutdown
    logger.info("Shutting down calibration API server")
    close_db()


app = FastAPI(
    title="Web Calibration API",
    description="API for web-based gaze calibration system",
    version="1.0.0",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(session.router, prefix="/api/calibration/session", tags=["session"])
app.include_router(calibration.router, prefix="/api/calibration", tags=["calibration"])
app.include_router(screen.router, prefix="/api/screen", tags=["screen"])

# Include debug router in development
if settings.DEBUG:
    from .api import debug

    app.include_router(debug.router, prefix="/api/debug", tags=["debug"])


@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "Web Calibration API", "version": "1.0.0", "status": "active"}


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "calibration-api"}


@app.get("/api/ping")
async def ping():
    """Ping endpoint for latency measurement"""
    return {"status": "pong"}


if __name__ == "__main__":
    try:
        import uvicorn

        print(f"Starting server on {settings.HOST}:{settings.PORT}")
        uvicorn.run(
            "backend.app:app", host=settings.HOST, port=settings.PORT, reload=settings.DEBUG
        )
    except Exception as e:
        import traceback

        print(f"Failed to start server: {e}")
        traceback.print_exc()
        sys.exit(1)
