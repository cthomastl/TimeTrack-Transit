"""Health check endpoints."""

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health", summary="Health check")
def health_check() -> dict:
    """Check if the API is running."""
    return {"status": "healthy", "service": "TimeTrack-Transit"}


@router.get("/", summary="Root endpoint")
def root() -> dict:
    """Root endpoint with API information."""
    return {
        "service": "TimeTrack-Transit",
        "description": "Bus Departure Tracking System for Humble, TX",
        "version": "1.0.0",
        "docs": "/docs",
    }
