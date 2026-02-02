"""Bus departure data models."""

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class DepartureStatus(str, Enum):
    """Status of a bus departure."""

    SCHEDULED = "scheduled"
    ON_TIME = "on_time"
    LATE = "late"
    DEPARTED = "departed"
    CANCELLED = "cancelled"


class BusDepartureCreate(BaseModel):
    """Schema for creating a new bus departure record."""

    bus_id: str = Field(..., description="Unique identifier for the bus")
    route_number: str = Field(..., description="Bus route number")
    scheduled_departure: datetime = Field(
        ..., description="Scheduled departure time"
    )
    driver_id: Optional[str] = Field(None, description="Driver identifier")
    destination: str = Field(..., description="Final destination of the route")


class BusDepartureUpdate(BaseModel):
    """Schema for updating a bus departure record."""

    actual_departure: Optional[datetime] = Field(
        None, description="Actual departure time"
    )
    status: Optional[DepartureStatus] = Field(None, description="Departure status")
    delay_reason: Optional[str] = Field(None, description="Reason for delay if late")
    driver_id: Optional[str] = Field(None, description="Driver identifier")


class BusDeparture(BaseModel):
    """Complete bus departure record."""

    departure_id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Unique departure record ID",
    )
    bus_id: str = Field(..., description="Unique identifier for the bus")
    route_number: str = Field(..., description="Bus route number")
    scheduled_departure: datetime = Field(
        ..., description="Scheduled departure time"
    )
    actual_departure: Optional[datetime] = Field(
        None, description="Actual departure time"
    )
    status: DepartureStatus = Field(
        default=DepartureStatus.SCHEDULED, description="Departure status"
    )
    delay_minutes: int = Field(default=0, description="Delay in minutes")
    delay_reason: Optional[str] = Field(None, description="Reason for delay if late")
    driver_id: Optional[str] = Field(None, description="Driver identifier")
    destination: str = Field(..., description="Final destination of the route")
    station_name: str = Field(
        default="Humble Transit Station", description="Departure station"
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="Record creation timestamp"
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow, description="Record update timestamp"
    )

    class Config:
        use_enum_values = True


class BusDepartureResponse(BaseModel):
    """API response for bus departure."""

    departure_id: str
    bus_id: str
    route_number: str
    scheduled_departure: datetime
    actual_departure: Optional[datetime]
    status: str
    delay_minutes: int
    delay_reason: Optional[str]
    driver_id: Optional[str]
    destination: str
    station_name: str
    is_late: bool = Field(..., description="Whether departure was late")


class LateDepartureReport(BaseModel):
    """Report for a single late departure."""

    departure_id: str
    bus_id: str
    route_number: str
    scheduled_departure: datetime
    actual_departure: datetime
    delay_minutes: int
    delay_reason: Optional[str]
    driver_id: Optional[str]
    destination: str


class LateDepartureSummary(BaseModel):
    """Summary of late departures for a time period."""

    start_date: datetime
    end_date: datetime
    total_departures: int
    late_departures: int
    on_time_percentage: float
    average_delay_minutes: float
    late_departure_details: list[LateDepartureReport]
