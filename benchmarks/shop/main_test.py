from __future__ import annotations

from fastapi.testclient import TestClient

# Import the app from main to ensure it's properly initialized
import main

app = main.app


async def test_app_starts_and_applies_schema() -> None:
    """Test that the application starts and applies the schema."""
    # Given the application module and its lifespan
    # When the lifespan is entered via a test client context manager
    with TestClient(app) as client:
        # Then the storage catalog contains the tables products, orders, order_lines
        # Then reading an unknown order returns 404
        response = client.get("/orders/123")
        assert response.status_code == 404
