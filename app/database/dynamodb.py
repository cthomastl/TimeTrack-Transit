"""DynamoDB client and operations for TimeTrack-Transit."""

import logging
from datetime import datetime
from decimal import Decimal
from functools import lru_cache
from typing import Any, Optional

import boto3
from botocore.exceptions import ClientError

from app.config import Settings, get_settings
from app.models.departure import BusDeparture, DepartureStatus

logger = logging.getLogger(__name__)


class DynamoDBClient:
    """Client for DynamoDB operations."""

    def __init__(self, settings: Settings):
        """Initialize DynamoDB client."""
        self.settings = settings
        self.table_name = settings.dynamodb_table_name

        # Configure boto3 client
        client_kwargs = {"region_name": settings.aws_region}

        if settings.aws_access_key_id and settings.aws_secret_access_key:
            client_kwargs["aws_access_key_id"] = settings.aws_access_key_id
            client_kwargs["aws_secret_access_key"] = settings.aws_secret_access_key

        if settings.dynamodb_endpoint_url:
            client_kwargs["endpoint_url"] = settings.dynamodb_endpoint_url

        self.dynamodb = boto3.resource("dynamodb", **client_kwargs)
        self.table = self.dynamodb.Table(self.table_name)
        self.client = boto3.client("dynamodb", **client_kwargs)

    def _serialize_datetime(self, dt: datetime) -> str:
        """Serialize datetime to ISO format string."""
        return dt.isoformat()

    def _deserialize_datetime(self, dt_str: str) -> datetime:
        """Deserialize ISO format string to datetime."""
        return datetime.fromisoformat(dt_str)

    def _serialize_item(self, departure: BusDeparture) -> dict[str, Any]:
        """Serialize BusDeparture to DynamoDB item format."""
        item = {
            "PK": f"DEPARTURE#{departure.departure_id}",
            "SK": f"SCHEDULED#{self._serialize_datetime(departure.scheduled_departure)}",
            "departure_id": departure.departure_id,
            "bus_id": departure.bus_id,
            "route_number": departure.route_number,
            "scheduled_departure": self._serialize_datetime(
                departure.scheduled_departure
            ),
            "status": departure.status,
            "delay_minutes": Decimal(str(departure.delay_minutes)),
            "destination": departure.destination,
            "station_name": departure.station_name,
            "created_at": self._serialize_datetime(departure.created_at),
            "updated_at": self._serialize_datetime(departure.updated_at),
            # GSI for querying by date
            "departure_date": departure.scheduled_departure.strftime("%Y-%m-%d"),
            # GSI for querying by route
            "route_date": f"{departure.route_number}#{departure.scheduled_departure.strftime('%Y-%m-%d')}",
            # GSI for querying late departures
            "status_date": f"{departure.status}#{departure.scheduled_departure.strftime('%Y-%m-%d')}",
        }

        if departure.actual_departure:
            item["actual_departure"] = self._serialize_datetime(
                departure.actual_departure
            )

        if departure.delay_reason:
            item["delay_reason"] = departure.delay_reason

        if departure.driver_id:
            item["driver_id"] = departure.driver_id

        return item

    def _deserialize_item(self, item: dict[str, Any]) -> BusDeparture:
        """Deserialize DynamoDB item to BusDeparture."""
        return BusDeparture(
            departure_id=item["departure_id"],
            bus_id=item["bus_id"],
            route_number=item["route_number"],
            scheduled_departure=self._deserialize_datetime(item["scheduled_departure"]),
            actual_departure=(
                self._deserialize_datetime(item["actual_departure"])
                if item.get("actual_departure")
                else None
            ),
            status=DepartureStatus(item["status"]),
            delay_minutes=int(item.get("delay_minutes", 0)),
            delay_reason=item.get("delay_reason"),
            driver_id=item.get("driver_id"),
            destination=item["destination"],
            station_name=item.get("station_name", "Humble Transit Station"),
            created_at=self._deserialize_datetime(item["created_at"]),
            updated_at=self._deserialize_datetime(item["updated_at"]),
        )

    def create_table_if_not_exists(self) -> bool:
        """Create DynamoDB table if it doesn't exist."""
        try:
            self.client.describe_table(TableName=self.table_name)
            logger.info(f"Table {self.table_name} already exists")
            return True
        except ClientError as e:
            if e.response["Error"]["Code"] == "ResourceNotFoundException":
                logger.info(f"Creating table {self.table_name}")
                self.client.create_table(
                    TableName=self.table_name,
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
                # Wait for table to be created
                waiter = self.client.get_waiter("table_exists")
                waiter.wait(TableName=self.table_name)
                logger.info(f"Table {self.table_name} created successfully")
                return True
            raise

    def put_departure(self, departure: BusDeparture) -> BusDeparture:
        """Store a bus departure record in DynamoDB."""
        try:
            item = self._serialize_item(departure)
            self.table.put_item(Item=item)
            logger.info(f"Stored departure: {departure.departure_id}")
            return departure
        except ClientError as e:
            logger.error(f"Error storing departure: {e}")
            raise

    def get_departure(self, departure_id: str) -> Optional[BusDeparture]:
        """Retrieve a bus departure record by ID."""
        try:
            # Query using begins_with since we know the PK but not the full SK
            response = self.table.query(
                KeyConditionExpression="PK = :pk",
                ExpressionAttributeValues={":pk": f"DEPARTURE#{departure_id}"},
            )

            items = response.get("Items", [])
            if items:
                return self._deserialize_item(items[0])
            return None
        except ClientError as e:
            logger.error(f"Error retrieving departure {departure_id}: {e}")
            raise

    def update_departure(
        self,
        departure_id: str,
        actual_departure: Optional[datetime] = None,
        status: Optional[DepartureStatus] = None,
        delay_reason: Optional[str] = None,
        delay_minutes: Optional[int] = None,
    ) -> Optional[BusDeparture]:
        """Update a bus departure record."""
        existing = self.get_departure(departure_id)
        if not existing:
            return None

        # Build update expression
        update_parts = ["#updated_at = :updated_at"]
        expr_names = {"#updated_at": "updated_at"}
        expr_values = {":updated_at": self._serialize_datetime(datetime.utcnow())}

        if actual_departure:
            update_parts.append("#actual_departure = :actual_departure")
            expr_names["#actual_departure"] = "actual_departure"
            expr_values[":actual_departure"] = self._serialize_datetime(actual_departure)

        if status:
            update_parts.append("#status = :status")
            expr_names["#status"] = "status"
            expr_values[":status"] = status.value
            # Update status_date GSI key
            update_parts.append("#status_date = :status_date")
            expr_names["#status_date"] = "status_date"
            expr_values[":status_date"] = (
                f"{status.value}#{existing.scheduled_departure.strftime('%Y-%m-%d')}"
            )

        if delay_reason:
            update_parts.append("#delay_reason = :delay_reason")
            expr_names["#delay_reason"] = "delay_reason"
            expr_values[":delay_reason"] = delay_reason

        if delay_minutes is not None:
            update_parts.append("#delay_minutes = :delay_minutes")
            expr_names["#delay_minutes"] = "delay_minutes"
            expr_values[":delay_minutes"] = Decimal(str(delay_minutes))

        try:
            sk = f"SCHEDULED#{self._serialize_datetime(existing.scheduled_departure)}"
            self.table.update_item(
                Key={"PK": f"DEPARTURE#{departure_id}", "SK": sk},
                UpdateExpression="SET " + ", ".join(update_parts),
                ExpressionAttributeNames=expr_names,
                ExpressionAttributeValues=expr_values,
            )
            return self.get_departure(departure_id)
        except ClientError as e:
            logger.error(f"Error updating departure {departure_id}: {e}")
            raise

    def get_departures_by_date(self, date: str) -> list[BusDeparture]:
        """Get all departures for a specific date (YYYY-MM-DD format)."""
        try:
            response = self.table.query(
                IndexName="DepartureDateIndex",
                KeyConditionExpression="departure_date = :date",
                ExpressionAttributeValues={":date": date},
            )
            return [self._deserialize_item(item) for item in response.get("Items", [])]
        except ClientError as e:
            logger.error(f"Error querying departures by date {date}: {e}")
            raise

    def get_late_departures_by_date(self, date: str) -> list[BusDeparture]:
        """Get all late departures for a specific date."""
        try:
            status_date = f"{DepartureStatus.LATE.value}#{date}"
            response = self.table.query(
                IndexName="StatusDateIndex",
                KeyConditionExpression="status_date = :status_date",
                ExpressionAttributeValues={":status_date": status_date},
            )
            return [self._deserialize_item(item) for item in response.get("Items", [])]
        except ClientError as e:
            logger.error(f"Error querying late departures by date {date}: {e}")
            raise

    def get_departures_by_route_and_date(
        self, route_number: str, date: str
    ) -> list[BusDeparture]:
        """Get all departures for a specific route on a specific date."""
        try:
            route_date = f"{route_number}#{date}"
            response = self.table.query(
                IndexName="RouteDateIndex",
                KeyConditionExpression="route_date = :route_date",
                ExpressionAttributeValues={":route_date": route_date},
            )
            return [self._deserialize_item(item) for item in response.get("Items", [])]
        except ClientError as e:
            logger.error(
                f"Error querying departures by route {route_number} and date {date}: {e}"
            )
            raise

    def delete_departure(self, departure_id: str) -> bool:
        """Delete a bus departure record."""
        existing = self.get_departure(departure_id)
        if not existing:
            return False

        try:
            sk = f"SCHEDULED#{self._serialize_datetime(existing.scheduled_departure)}"
            self.table.delete_item(Key={"PK": f"DEPARTURE#{departure_id}", "SK": sk})
            logger.info(f"Deleted departure: {departure_id}")
            return True
        except ClientError as e:
            logger.error(f"Error deleting departure {departure_id}: {e}")
            raise


@lru_cache()
def get_dynamodb_client() -> DynamoDBClient:
    """Get cached DynamoDB client instance."""
    return DynamoDBClient(get_settings())
