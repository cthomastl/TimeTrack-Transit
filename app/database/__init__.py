"""Database layer for DynamoDB operations."""

from app.database.dynamodb import DynamoDBClient, get_dynamodb_client

__all__ = ["DynamoDBClient", "get_dynamodb_client"]
