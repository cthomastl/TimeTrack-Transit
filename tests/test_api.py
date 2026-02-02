"""Tests for API endpoints."""

from datetime import datetime, timedelta

import pytest
from moto import mock_aws


@mock_aws
class TestHealthEndpoints:
    """Test health check endpoints."""

    def test_health_check(self, test_client):
        """Test health check endpoint."""
        response = test_client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "TimeTrack-Transit"

    def test_root_endpoint(self, test_client):
        """Test root endpoint."""
        response = test_client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "TimeTrack-Transit"
        assert "version" in data


@mock_aws
class TestDepartureEndpoints:
    """Test departure CRUD endpoints."""

    def test_create_departure(self, test_client, sample_departure_data):
        """Test creating a new departure."""
        response = test_client.post("/api/v1/departures", json=sample_departure_data)
        assert response.status_code == 201
        data = response.json()
        assert data["bus_id"] == sample_departure_data["bus_id"]
        assert data["route_number"] == sample_departure_data["route_number"]
        assert data["status"] == "scheduled"
        assert "departure_id" in data

    def test_get_departure(self, test_client, sample_departure_data):
        """Test getting a departure by ID."""
        # Create a departure first
        create_response = test_client.post(
            "/api/v1/departures", json=sample_departure_data
        )
        departure_id = create_response.json()["departure_id"]

        # Get the departure
        response = test_client.get(f"/api/v1/departures/{departure_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["departure_id"] == departure_id
        assert data["bus_id"] == sample_departure_data["bus_id"]

    def test_get_nonexistent_departure(self, test_client):
        """Test getting a departure that doesn't exist."""
        response = test_client.get("/api/v1/departures/nonexistent-id")
        assert response.status_code == 404

    def test_record_on_time_departure(self, test_client, sample_departure_data):
        """Test recording an on-time departure."""
        # Create a departure
        create_response = test_client.post(
            "/api/v1/departures", json=sample_departure_data
        )
        departure_id = create_response.json()["departure_id"]
        scheduled = datetime.fromisoformat(sample_departure_data["scheduled_departure"])

        # Record actual departure (on time)
        actual_time = scheduled + timedelta(minutes=2)
        response = test_client.post(
            f"/api/v1/departures/{departure_id}/record-departure",
            params={"actual_time": actual_time.isoformat()},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "on_time"
        assert data["is_late"] is False

    def test_record_late_departure(self, test_client, sample_departure_data):
        """Test recording a late departure."""
        # Create a departure
        create_response = test_client.post(
            "/api/v1/departures", json=sample_departure_data
        )
        departure_id = create_response.json()["departure_id"]
        scheduled = datetime.fromisoformat(sample_departure_data["scheduled_departure"])

        # Record actual departure (late - 10 minutes after scheduled)
        actual_time = scheduled + timedelta(minutes=10)
        response = test_client.post(
            f"/api/v1/departures/{departure_id}/record-departure",
            params={
                "actual_time": actual_time.isoformat(),
                "delay_reason": "Traffic congestion",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "late"
        assert data["is_late"] is True
        assert data["delay_minutes"] == 10
        assert data["delay_reason"] == "Traffic congestion"

    def test_cancel_departure(self, test_client, sample_departure_data):
        """Test cancelling a departure."""
        # Create a departure
        create_response = test_client.post(
            "/api/v1/departures", json=sample_departure_data
        )
        departure_id = create_response.json()["departure_id"]

        # Cancel the departure
        response = test_client.post(f"/api/v1/departures/{departure_id}/cancel")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "cancelled"

    def test_delete_departure(self, test_client, sample_departure_data):
        """Test deleting a departure."""
        # Create a departure
        create_response = test_client.post(
            "/api/v1/departures", json=sample_departure_data
        )
        departure_id = create_response.json()["departure_id"]

        # Delete the departure
        response = test_client.delete(f"/api/v1/departures/{departure_id}")
        assert response.status_code == 204

        # Verify it's deleted
        response = test_client.get(f"/api/v1/departures/{departure_id}")
        assert response.status_code == 404


@mock_aws
class TestQueryEndpoints:
    """Test query and report endpoints."""

    def test_get_departures_by_date(self, test_client, sample_departure_data):
        """Test getting departures by date."""
        # Create a departure
        test_client.post("/api/v1/departures", json=sample_departure_data)

        # Query by date
        scheduled = datetime.fromisoformat(sample_departure_data["scheduled_departure"])
        date_str = scheduled.strftime("%Y-%m-%d")
        response = test_client.get(f"/api/v1/departures?date={date_str}")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_get_departures_invalid_date_format(self, test_client):
        """Test getting departures with invalid date format."""
        response = test_client.get("/api/v1/departures?date=invalid")
        assert response.status_code == 422
