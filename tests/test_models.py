"""Tests for data models."""

from datetime import datetime

import pytest

from app.models.departure import (
    BusDeparture,
    BusDepartureCreate,
    DepartureStatus,
)


class TestBusDepartureModels:
    """Test bus departure models."""

    def test_create_departure_model(self):
        """Test creating a BusDepartureCreate model."""
        data = BusDepartureCreate(
            bus_id="BUS-001",
            route_number="101",
            scheduled_departure=datetime.utcnow(),
            driver_id="DRV-001",
            destination="Houston Downtown",
        )
        assert data.bus_id == "BUS-001"
        assert data.route_number == "101"
        assert data.destination == "Houston Downtown"

    def test_bus_departure_defaults(self):
        """Test BusDeparture default values."""
        departure = BusDeparture(
            bus_id="BUS-001",
            route_number="101",
            scheduled_departure=datetime.utcnow(),
            destination="Houston Downtown",
        )
        assert departure.status == DepartureStatus.SCHEDULED
        assert departure.delay_minutes == 0
        assert departure.actual_departure is None
        assert departure.delay_reason is None
        assert departure.departure_id is not None

    def test_departure_status_enum(self):
        """Test DepartureStatus enum values."""
        assert DepartureStatus.SCHEDULED.value == "scheduled"
        assert DepartureStatus.ON_TIME.value == "on_time"
        assert DepartureStatus.LATE.value == "late"
        assert DepartureStatus.DEPARTED.value == "departed"
        assert DepartureStatus.CANCELLED.value == "cancelled"
