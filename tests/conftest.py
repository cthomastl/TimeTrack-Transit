"""Test configuration and fixtures."""

import os
from datetime import datetime, timedelta

import boto3
import pytest
from fastapi.testclient import TestClient
from moto import mock_aws

# Set test environment variables before imports
os.environ["AWS_REGION"] = "us-east-1"
os.environ["AWS_ACCESS_KEY_ID"] = "testing"
os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
os.environ["DYNAMODB_TABLE_NAME"] = "TimeTrack-Transit-DB-Test"
os.environ["APP_ENV"] = "testing"


@pytest.fixture
def aws_credentials():
    """Mock AWS Credentials for moto."""
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"
    os.environ["AWS_DEFAULT_REGION"] = "us-east-1"


@pytest.fixture
def dynamodb_table(aws_credentials):
    """Create a mock DynamoDB table for testing."""
    with mock_aws():
        client = boto3.client("dynamodb", region_name="us-east-1")
        client.create_table(
            TableName="TimeTrack-Transit-DB-Test",
            KeySchema=[
                {"AttributeName": "PK", "KeyType": "HASH"},
                {"AttributeName": "SK", "KeyType": "RANGE"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "PK", "AttributeType": "S"},
                {"AttributeName": "SK", "AttributeType": "S"},
                {"AttributeName": "departure_date", "AttributeType": "S"},
                {"AttributeName": "status_date", "AttributeType": "S"},
                {"AttributeName": "route_date", "AttributeType": "S"},
            ],
            GlobalSecondaryIndexes=[
                {
                    "IndexName": "DepartureDateIndex",
                    "KeySchema": [
                        {"AttributeName": "departure_date", "KeyType": "HASH"},
                        {"AttributeName": "SK", "KeyType": "RANGE"},
                    ],
                    "Projection": {"ProjectionType": "ALL"},
                },
                {
                    "IndexName": "StatusDateIndex",
                    "KeySchema": [
                        {"AttributeName": "status_date", "KeyType": "HASH"},
                        {"AttributeName": "SK", "KeyType": "RANGE"},
                    ],
                    "Projection": {"ProjectionType": "ALL"},
                },
                {
                    "IndexName": "RouteDateIndex",
                    "KeySchema": [
                        {"AttributeName": "route_date", "KeyType": "HASH"},
                        {"AttributeName": "SK", "KeyType": "RANGE"},
                    ],
                    "Projection": {"ProjectionType": "ALL"},
                },
            ],
            BillingMode="PAY_PER_REQUEST",
        )
        yield client


@pytest.fixture
def test_client(dynamodb_table):
    """Create a test client with mocked DynamoDB."""
    from app.main import app

    with TestClient(app) as client:
        yield client


@pytest.fixture
def sample_departure_data():
    """Sample departure data for testing."""
    scheduled_time = datetime.utcnow() + timedelta(hours=1)
    return {
        "bus_id": "BUS-001",
        "route_number": "101",
        "scheduled_departure": scheduled_time.isoformat(),
        "driver_id": "DRV-001",
        "destination": "Houston Downtown",
    }


@pytest.fixture
def late_departure_time():
    """Generate a time that would be considered late (10 minutes after scheduled)."""
    return timedelta(minutes=10)
