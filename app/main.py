"""Main FastAPI application for TimeTrack-Transit."""

import logging
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.health import router as health_router
from app.api.routes import router as api_router
from app.config import get_settings
from app.database.dynamodb import get_dynamodb_client


def setup_logging() -> None:
    """Configure structured logging."""
    settings = get_settings()

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
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    logging.basicConfig(
        format="%(message)s",
        level=getattr(logging, settings.log_level.upper()),
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    setup_logging()
    logger = logging.getLogger(__name__)
    settings = get_settings()

    logger.info(f"Starting TimeTrack-Transit in {settings.app_env} mode")
    logger.info(f"Station: {settings.station_name}")
    logger.info(f"DynamoDB Table: {settings.dynamodb_table_name}")

    # Initialize DynamoDB table if needed (for local development)
    if settings.app_env == "development":
        try:
            db_client = get_dynamodb_client()
            db_client.create_table_if_not_exists()
        except Exception as e:
            logger.warning(f"Could not initialize DynamoDB table: {e}")

    yield

    # Shutdown
    logger.info("Shutting down TimeTrack-Transit")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title="TimeTrack-Transit",
        description=(
            "Bus Departure Tracking System for Humble, TX. "
            "Track scheduled and actual departure times, identify late departures, "
            "and generate performance reports."
        ),
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # Add CORS middleware for API access
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    app.include_router(health_router)
    app.include_router(api_router)

    return app


# Create app instance
app = create_app()


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "app.main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.app_env == "development",
    )
