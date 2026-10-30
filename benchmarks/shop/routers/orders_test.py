from unittest.mock import MagicMock

from fastapi import FastAPI, status
from fastapi.testclient import TestClient
from routers.orders import make_orders_router
from services.checkout import (
    CheckoutStorageError,
    CheckoutValidationError,
)


def test_create_returns_201():
    mock_service = MagicMock()
    mock_service.checkout.return_value = {
        "order_id": "o1",
        "customer_id": "c1",
        "status": "PENDING",
        "created_at": "2023-01-01T00:00:00.000000+00:00",
        "lines": [
            {
                "product_id": "p1",
                "qty": 1,
                "unit_amount": "10.00",
                "unit_currency": "USD",
            }
        ],
    }

    app = FastAPI()
    app.include_router(make_orders_router(mock_service))

    with TestClient(app) as client:
        response = client.post(
            "/orders/",
            json={
                "customer_id": "c1",
                "order_id": "o1",
                "lines": [
                    {
                        "product_id": "p1",
                        "qty": 1,
                        "unit_amount": "10.00",
                        "unit_currency": "USD",
                    }
                ],
            },
        )

    assert response.status_code == status.HTTP_201_CREATED
    assert response.json()["status"] == "PENDING"
    assert response.json()["created_at"] == "2023-01-01T00:00:00.000000+00:00"
def test_create_with_empty_lines_returns_400():
    mock_service = MagicMock()
    mock_service.checkout.side_effect = CheckoutValidationError("lines must not be empty")

    app = FastAPI()
    app.include_router(make_orders_router(mock_service))

    with TestClient(app) as client:
        response = client.post(
            "/orders/",
            json={
                "customer_id": "c1",
                "order_id": "o1",
                "lines": [],
            },
        )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["detail"] == "lines must not be empty"
def test_create_with_missing_product_returns_400():
    mock_service = MagicMock()
    mock_service.checkout.side_effect = CheckoutValidationError("product not found")

    app = FastAPI()
    app.include_router(make_orders_router(mock_service))

    with TestClient(app) as client:
        response = client.post(
            "/orders/",
            json={
                "customer_id": "c1",
                "order_id": "o1",
                "lines": [
                    {
                        "product_id": "p1",
                        "qty": 1,
                        "unit_amount": "10.00",
                        "unit_currency": "USD",
                    }
                ],
            },
        )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["detail"] == "product not found"
def test_create_with_duplicate_order_returns_409():
    mock_service = MagicMock()
    mock_service.checkout.side_effect = CheckoutStorageError("order already exists")

    app = FastAPI()
    app.include_router(make_orders_router(mock_service))

    with TestClient(app) as client:
        response = client.post(
            "/orders/",
            json={
                "customer_id": "c1",
                "order_id": "o1",
                "lines": [
                    {
                        "product_id": "p1",
                        "qty": 1,
                        "unit_amount": "10.00",
                        "unit_currency": "USD",
                    }
                ],
            },
        )

    assert response.status_code == status.HTTP_409_CONFLICT
    assert response.json()["detail"] == "order already exists"
def test_create_does_not_dispatch_on_message_text():
    mock_service = MagicMock()
    mock_service.checkout.side_effect = CheckoutStorageError("lines must not be empty")

    app = FastAPI()
    app.include_router(make_orders_router(mock_service))

    with TestClient(app) as client:
        response = client.post(
            "/orders/",
            json={
                "customer_id": "c1",
                "order_id": "o1",
                "lines": [],
            },
        )

    assert response.status_code == status.HTTP_409_CONFLICT
    assert response.json()["detail"] == "lines must not be empty"
def test_create_with_unexpected_exception_returns_500():
    mock_service = MagicMock()
    mock_service.checkout.side_effect = RuntimeError("boom")

    app = FastAPI()
    app.include_router(make_orders_router(mock_service))

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post(
            "/orders/",
            json={
                "customer_id": "c1",
                "order_id": "o1",
                "lines": [
                    {
                        "product_id": "p1",
                        "qty": 1,
                        "unit_amount": "10.00",
                        "unit_currency": "USD",
                    }
                ],
            },
        )

    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
