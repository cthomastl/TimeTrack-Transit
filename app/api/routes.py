"""API routes for bus departure tracking."""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.models.departure import (
    BusDepartureCreate,
    BusDepartureResponse,
    BusDepartureUpdate,
    LateDepartureSummary,
    LogDepartureRequest,
    LogDepartureResponse,
)
from app.services.departure_service import DepartureService, get_departure_service

router = APIRouter(prefix="/api/v1", tags=["departures"])


@router.post(
    "/departures",
    response_model=BusDepartureResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Schedule a new bus departure",
)
def create_departure(
    departure_data: BusDepartureCreate,
    service: DepartureService = Depends(get_departure_service),
) -> BusDepartureResponse:
    """
    Schedule a new bus departure from Humble Transit Station.

    - **bus_id**: Unique identifier for the bus
    - **route_number**: Bus route number (e.g., "101", "202")
    - **scheduled_departure**: Scheduled departure time
    - **driver_id**: Optional driver identifier
    - **destination**: Final destination of the route
    """
    return service.create_departure(departure_data)


@router.get(
    "/departures/{departure_id}",
    response_model=BusDepartureResponse,
    summary="Get a specific departure",
)
def get_departure(
    departure_id: str,
    service: DepartureService = Depends(get_departure_service),
) -> BusDepartureResponse:
    """Retrieve a specific bus departure record by ID."""
    departure = service.get_departure(departure_id)
    if not departure:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Departure {departure_id} not found",
        )
    return departure


@router.put(
    "/departures/{departure_id}",
    response_model=BusDepartureResponse,
    summary="Update a departure",
)
def update_departure(
    departure_id: str,
    update_data: BusDepartureUpdate,
    service: DepartureService = Depends(get_departure_service),
) -> BusDepartureResponse:
    """Update a bus departure record."""
    departure = service.update_departure(departure_id, update_data)
    if not departure:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Departure {departure_id} not found",
        )
    return departure


@router.post(
    "/departures/{departure_id}/record-departure",
    response_model=BusDepartureResponse,
    summary="Record actual departure time",
)
def record_actual_departure(
    departure_id: str,
    actual_time: datetime = Query(..., description="Actual departure time"),
    delay_reason: Optional[str] = Query(None, description="Reason for delay if late"),
    service: DepartureService = Depends(get_departure_service),
) -> BusDepartureResponse:
    """
    Record when a bus actually departed from the station.

    This will automatically calculate if the departure was late and update
    the status accordingly. If the bus departed more than 5 minutes after
    the scheduled time, it will be marked as LATE.
    """
    departure = service.record_actual_departure(departure_id, actual_time, delay_reason)
    if not departure:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Departure {departure_id} not found",
        )
    return departure


@router.post(
    "/departures/{departure_id}/cancel",
    response_model=BusDepartureResponse,
    summary="Cancel a departure",
)
def cancel_departure(
    departure_id: str,
    service: DepartureService = Depends(get_departure_service),
) -> BusDepartureResponse:
    """Cancel a scheduled bus departure."""
    departure = service.cancel_departure(departure_id)
    if not departure:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Departure {departure_id} not found",
        )
    return departure


@router.delete(
    "/departures/{departure_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a departure",
)
def delete_departure(
    departure_id: str,
    service: DepartureService = Depends(get_departure_service),
) -> None:
    """Delete a bus departure record."""
    deleted = service.delete_departure(departure_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Departure {departure_id} not found",
        )


@router.get(
    "/departures",
    response_model=list[BusDepartureResponse],
    summary="Get departures for a date",
)
def get_departures_by_date(
    date: str = Query(
        ...,
        description="Date in YYYY-MM-DD format",
        regex=r"^\d{4}-\d{2}-\d{2}$",
    ),
    service: DepartureService = Depends(get_departure_service),
) -> list[BusDepartureResponse]:
    """Get all bus departures for a specific date."""
    return service.get_departures_for_date(date)


@router.get(
    "/departures/late",
    response_model=list[BusDepartureResponse],
    summary="Get late departures for a date",
)
def get_late_departures(
    date: str = Query(
        ...,
        description="Date in YYYY-MM-DD format",
        regex=r"^\d{4}-\d{2}-\d{2}$",
    ),
    service: DepartureService = Depends(get_departure_service),
) -> list[BusDepartureResponse]:
    """Get all late bus departures for a specific date."""
    return service.get_late_departures_for_date(date)


@router.get(
    "/departures/route/{route_number}",
    response_model=list[BusDepartureResponse],
    summary="Get departures by route",
)
def get_departures_by_route(
    route_number: str,
    date: str = Query(
        ...,
        description="Date in YYYY-MM-DD format",
        regex=r"^\d{4}-\d{2}-\d{2}$",
    ),
    service: DepartureService = Depends(get_departure_service),
) -> list[BusDepartureResponse]:
    """Get all departures for a specific route on a specific date."""
    return service.get_departures_by_route(route_number, date)


@router.get(
    "/reports/late-departures",
    response_model=LateDepartureSummary,
    summary="Get late departure summary report",
)
def get_late_departure_report(
    start_date: str = Query(
        ...,
        description="Start date in YYYY-MM-DD format",
        regex=r"^\d{4}-\d{2}-\d{2}$",
    ),
    end_date: str = Query(
        ...,
        description="End date in YYYY-MM-DD format",
        regex=r"^\d{4}-\d{2}-\d{2}$",
    ),
    service: DepartureService = Depends(get_departure_service),
) -> LateDepartureSummary:
    """
    Generate a summary report of late departures for a date range.

    Returns statistics including:
    - Total departures
    - Number of late departures
    - On-time percentage
    - Average delay in minutes
    - Details of each late departure
    """
    return service.get_late_departure_summary(start_date, end_date)


@router.post(
    "/log-departure",
    response_model=LogDepartureResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Log a bus departure with delay calculation",
)
def log_departure(
    request: LogDepartureRequest,
    service: DepartureService = Depends(get_departure_service),
) -> LogDepartureResponse:
    """
    Log a bus departure and automatically calculate if it was late.

    This simplified endpoint accepts:
    - **bus_id**: Unique identifier for the bus
    - **scheduled_time**: When the bus was scheduled to depart
    - **actual_time**: When the bus actually departed

    The endpoint calculates the delay in minutes and sets `is_late` to True
    if the delay exceeds the configured threshold (default: 5 minutes).
    The departure is automatically saved to DynamoDB.
    """
    return service.log_departure(request)
