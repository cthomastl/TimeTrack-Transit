"""Business logic service for bus departure tracking."""

import logging
from datetime import datetime, timedelta
from functools import lru_cache
from typing import Optional

from app.config import Settings, get_settings
from app.database.dynamodb import DynamoDBClient, get_dynamodb_client
from app.models.departure import (
    BusDeparture,
    BusDepartureCreate,
    BusDepartureResponse,
    BusDepartureUpdate,
    DepartureStatus,
    LateDepartureReport,
    LateDepartureSummary,
)

logger = logging.getLogger(__name__)


class DepartureService:
    """Service for managing bus departures and tracking late departures."""

    def __init__(self, db_client: DynamoDBClient, settings: Settings):
        """Initialize departure service."""
        self.db = db_client
        self.settings = settings
        self.late_threshold_minutes = settings.late_threshold_minutes

    def create_departure(self, departure_data: BusDepartureCreate) -> BusDepartureResponse:
        """Create a new scheduled bus departure."""
        departure = BusDeparture(
            bus_id=departure_data.bus_id,
            route_number=departure_data.route_number,
            scheduled_departure=departure_data.scheduled_departure,
            driver_id=departure_data.driver_id,
            destination=departure_data.destination,
            station_name=self.settings.station_name,
            status=DepartureStatus.SCHEDULED,
        )

        saved = self.db.put_departure(departure)
        logger.info(
            f"Created departure {saved.departure_id} for bus {saved.bus_id} "
            f"on route {saved.route_number}"
        )
        return self._to_response(saved)

    def get_departure(self, departure_id: str) -> Optional[BusDepartureResponse]:
        """Get a departure by ID."""
        departure = self.db.get_departure(departure_id)
        if departure:
            return self._to_response(departure)
        return None

    def record_actual_departure(
        self, departure_id: str, actual_time: datetime, delay_reason: Optional[str] = None
    ) -> Optional[BusDepartureResponse]:
        """Record when a bus actually departed and calculate if it was late."""
        departure = self.db.get_departure(departure_id)
        if not departure:
            logger.warning(f"Departure {departure_id} not found")
            return None

        # Calculate delay
        delay = actual_time - departure.scheduled_departure
        delay_minutes = int(delay.total_seconds() / 60)

        # Determine status based on delay
        if delay_minutes <= 0:
            status = DepartureStatus.ON_TIME
            delay_minutes = 0
        elif delay_minutes <= self.late_threshold_minutes:
            status = DepartureStatus.ON_TIME
        else:
            status = DepartureStatus.LATE
            logger.warning(
                f"LATE DEPARTURE: Bus {departure.bus_id} on route {departure.route_number} "
                f"departed {delay_minutes} minutes late"
            )

        # Update the record
        updated = self.db.update_departure(
            departure_id=departure_id,
            actual_departure=actual_time,
            status=status,
            delay_minutes=delay_minutes,
            delay_reason=delay_reason if status == DepartureStatus.LATE else None,
        )

        if updated:
            return self._to_response(updated)
        return None

    def update_departure(
        self, departure_id: str, update_data: BusDepartureUpdate
    ) -> Optional[BusDepartureResponse]:
        """Update a departure record."""
        departure = self.db.get_departure(departure_id)
        if not departure:
            return None

        delay_minutes = None
        if update_data.actual_departure and departure.scheduled_departure:
            delay = update_data.actual_departure - departure.scheduled_departure
            delay_minutes = max(0, int(delay.total_seconds() / 60))

        updated = self.db.update_departure(
            departure_id=departure_id,
            actual_departure=update_data.actual_departure,
            status=update_data.status,
            delay_reason=update_data.delay_reason,
            delay_minutes=delay_minutes,
        )

        if updated:
            return self._to_response(updated)
        return None

    def cancel_departure(self, departure_id: str) -> Optional[BusDepartureResponse]:
        """Cancel a scheduled departure."""
        updated = self.db.update_departure(
            departure_id=departure_id, status=DepartureStatus.CANCELLED
        )
        if updated:
            logger.info(f"Cancelled departure {departure_id}")
            return self._to_response(updated)
        return None

    def get_departures_for_date(self, date: str) -> list[BusDepartureResponse]:
        """Get all departures for a specific date."""
        departures = self.db.get_departures_by_date(date)
        return [self._to_response(d) for d in departures]

    def get_late_departures_for_date(self, date: str) -> list[BusDepartureResponse]:
        """Get all late departures for a specific date."""
        departures = self.db.get_late_departures_by_date(date)
        return [self._to_response(d) for d in departures]

    def get_departures_by_route(
        self, route_number: str, date: str
    ) -> list[BusDepartureResponse]:
        """Get all departures for a specific route on a date."""
        departures = self.db.get_departures_by_route_and_date(route_number, date)
        return [self._to_response(d) for d in departures]

    def get_late_departure_summary(
        self, start_date: str, end_date: str
    ) -> LateDepartureSummary:
        """Generate a summary report of late departures for a date range."""
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")

        all_departures: list[BusDeparture] = []
        late_departures: list[BusDeparture] = []

        # Iterate through each day in the range
        current = start
        while current <= end:
            date_str = current.strftime("%Y-%m-%d")
            daily_departures = self.db.get_departures_by_date(date_str)
            all_departures.extend(daily_departures)

            daily_late = self.db.get_late_departures_by_date(date_str)
            late_departures.extend(daily_late)

            current += timedelta(days=1)

        # Calculate statistics
        total_departures = len(all_departures)
        total_late = len(late_departures)

        on_time_percentage = (
            ((total_departures - total_late) / total_departures * 100)
            if total_departures > 0
            else 100.0
        )

        average_delay = (
            sum(d.delay_minutes for d in late_departures) / total_late
            if total_late > 0
            else 0.0
        )

        # Build late departure details
        late_details = [
            LateDepartureReport(
                departure_id=d.departure_id,
                bus_id=d.bus_id,
                route_number=d.route_number,
                scheduled_departure=d.scheduled_departure,
                actual_departure=d.actual_departure,
                delay_minutes=d.delay_minutes,
                delay_reason=d.delay_reason,
                driver_id=d.driver_id,
                destination=d.destination,
            )
            for d in late_departures
            if d.actual_departure  # Only include if actual departure is recorded
        ]

        return LateDepartureSummary(
            start_date=start,
            end_date=end,
            total_departures=total_departures,
            late_departures=total_late,
            on_time_percentage=round(on_time_percentage, 2),
            average_delay_minutes=round(average_delay, 2),
            late_departure_details=late_details,
        )

    def delete_departure(self, departure_id: str) -> bool:
        """Delete a departure record."""
        return self.db.delete_departure(departure_id)

    def _to_response(self, departure: BusDeparture) -> BusDepartureResponse:
        """Convert BusDeparture model to API response."""
        is_late = (
            departure.status == DepartureStatus.LATE
            or departure.delay_minutes > self.late_threshold_minutes
        )

        return BusDepartureResponse(
            departure_id=departure.departure_id,
            bus_id=departure.bus_id,
            route_number=departure.route_number,
            scheduled_departure=departure.scheduled_departure,
            actual_departure=departure.actual_departure,
            status=departure.status,
            delay_minutes=departure.delay_minutes,
            delay_reason=departure.delay_reason,
            driver_id=departure.driver_id,
            destination=departure.destination,
            station_name=departure.station_name,
            is_late=is_late,
        )


@lru_cache()
def get_departure_service() -> DepartureService:
    """Get cached departure service instance."""
    return DepartureService(get_dynamodb_client(), get_settings())
