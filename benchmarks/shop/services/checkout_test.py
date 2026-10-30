from unittest.mock import ANY, MagicMock

import pytest
from services.checkout import (
    CheckoutService,
    CheckoutStorageError,
    CheckoutValidationError,
    OrderLineRepository,
    OrderRepository,
    ProductRepository,
)


def test_checkout_persists_order_and_lines():
    # arrange
    products = MagicMock(spec=ProductRepository)
    orders = MagicMock(spec=OrderRepository)
    lines = MagicMock(spec=OrderLineRepository)
    sut = CheckoutService(products, orders, lines)

    products.get.return_value = {
        "product_id": "p1",
        "name": "Product 1",
        "price_amount": "10.00",
        "price_currency": "USD",
        "stock": 10,
    }

    # act
    result = sut.checkout(
        lines=[
            {
                "product_id": "p1",
                "qty": 1,
            }
        ],
        customer_id="c1",
        order_id="o1",
    )

    # assert
    assert len(result) == 5
    assert result["status"] == "PENDING"
    assert result["created_at"] is not None
    assert isinstance(result["created_at"], str)
    assert len(result["lines"]) == 1
    assert result["lines"][0]["product_id"] == "p1"

    orders.insert.assert_called_once_with("o1", "c1", "PENDING", result["created_at"])
    lines.insert.assert_called_once_with(
        "o1",
        "p1",
        1,
        "10.00",
        "USD",
    )
def test_empty_lines_raises_checkoutvalidationerror():
    # arrange
    products = MagicMock(spec=ProductRepository)
    orders = MagicMock(spec=OrderRepository)
    lines = MagicMock(spec=OrderLineRepository)
    sut = CheckoutService(products, orders, lines)

    # act
    with pytest.raises(CheckoutValidationError):
        sut.checkout(
            lines=[],
            customer_id="c1",
            order_id="o1",
        )

    # assert
    orders.insert.assert_not_called()
    lines.insert.assert_not_called()
def test_missing_product_raises_checkoutvalidationerror():
    # arrange
    products = MagicMock(spec=ProductRepository)
    orders = MagicMock(spec=OrderRepository)
    lines = MagicMock(spec=OrderLineRepository)
    sut = CheckoutService(products, orders, lines)

    products.get.return_value = None

    # act
    with pytest.raises(CheckoutValidationError):
        sut.checkout(
            lines=[
                {
                    "product_id": "p1",
                    "qty": 1,
                }
            ],
            customer_id="c1",
            order_id="o1",
        )

    # assert
    orders.insert.assert_not_called()
    lines.insert.assert_not_called()
def test_insufficient_stock_raises_checkoutvalidationerror():
    # arrange
    products = MagicMock(spec=ProductRepository)
    orders = MagicMock(spec=OrderRepository)
    lines = MagicMock(spec=OrderLineRepository)
    sut = CheckoutService(products, orders, lines)

    products.get.return_value = {
        "product_id": "p1",
        "name": "Product 1",
        "price_amount": "10.00",
        "price_currency": "USD",
        "stock": 2,
    }

    # act
    with pytest.raises(CheckoutValidationError):
        sut.checkout(
            lines=[
                {
                    "product_id": "p1",
                    "qty": 5,
                }
            ],
            customer_id="c1",
            order_id="o1",
        )

    # assert
    orders.insert.assert_not_called()
    lines.insert.assert_not_called()
def test_duplicate_product_raises_checkoutvalidationerror():
    # arrange
    products = MagicMock(spec=ProductRepository)
    orders = MagicMock(spec=OrderRepository)
    lines = MagicMock(spec=OrderLineRepository)
    sut = CheckoutService(products, orders, lines)

    products.get.side_effect = [
        {
            "product_id": "p1",
            "name": "Product 1",
            "price_amount": "10.00",
            "price_currency": "USD",
            "stock": 10,
        },
        {
            "product_id": "p1",
            "name": "Product 1",
            "price_amount": "10.00",
            "price_currency": "USD",
            "stock": 10,
        },
    ]

    # act
    with pytest.raises(CheckoutValidationError):
        sut.checkout(
            lines=[
                {
                    "product_id": "p1",
                    "qty": 1,
                },
                {
                    "product_id": "p1",
                    "qty": 2,
                },
            ],
            customer_id="c1",
            order_id="o1",
        )

    # assert
    orders.insert.assert_not_called()
    lines.insert.assert_not_called()
def test_header_storage_rejection_raises_checkoutstorageerror():
    # arrange
    products = MagicMock(spec=ProductRepository)
    orders = MagicMock(spec=OrderRepository)
    lines = MagicMock(spec=OrderLineRepository)
    sut = CheckoutService(products, orders, lines)

    products.get.return_value = {
        "product_id": "p1",
        "name": "Product 1",
        "price_amount": "10.00",
        "price_currency": "USD",
        "stock": 10,
    }

    orders.insert.side_effect = Exception("storage error")

    # act
    with pytest.raises(CheckoutStorageError) as exc_info:
        sut.checkout(
            lines=[
                {
                    "product_id": "p1",
                    "qty": 1,
                }
            ],
            customer_id="c1",
            order_id="o1",
        )

    # assert
    assert exc_info.value.__cause__ is not None
    assert exc_info.value.__cause__.args[0] == "storage error"
    orders.insert.assert_called_once_with("o1", "c1", "PENDING", ANY)
    lines.insert.assert_not_called()
def test_line_storage_rejection_raises_checkoutstorageerror():
    # arrange
    products = MagicMock(spec=ProductRepository)
    orders = MagicMock(spec=OrderRepository)
    lines = MagicMock(spec=OrderLineRepository)
    sut = CheckoutService(products, orders, lines)

    products.get.return_value = {
        "product_id": "p1",
        "name": "Product 1",
        "price_amount": "10.00",
        "price_currency": "USD",
        "stock": 10,
    }

    lines.insert.side_effect = Exception("storage error")

    # act
    with pytest.raises(CheckoutStorageError) as exc_info:
        sut.checkout(
            lines=[
                {
                    "product_id": "p1",
                    "qty": 1,
                }
            ],
            customer_id="c1",
            order_id="o1",
        )

    # assert
    assert exc_info.value.__cause__ is not None
    assert exc_info.value.__cause__.args[0] == "storage error"
    orders.insert.assert_called_once_with("o1", "c1", "PENDING", ANY)
    lines.insert.assert_called_once_with(
        "o1",
        "p1",
        1,
        "10.00",
        "USD",
    )
def test_storage_error_is_a_subclass_of_checkouterror_not_validation():
    # arrange
    products = MagicMock(spec=ProductRepository)
    orders = MagicMock(spec=OrderRepository)
    lines = MagicMock(spec=OrderLineRepository)
    sut = CheckoutService(products, orders, lines)

    products.get.return_value = {
        "product_id": "p1",
        "name": "Product 1",
        "price_amount": "10.00",
        "price_currency": "USD",
        "stock": 10,
    }

    orders.insert.side_effect = Exception("storage error")

    # act
    with pytest.raises(CheckoutStorageError) as exc_info:
        sut.checkout(
            lines=[
                {
                    "product_id": "p1",
                    "qty": 1,
                }
            ],
            customer_id="c1",
            order_id="o1",
        )

    # assert
    assert isinstance(exc_info.value, CheckoutStorageError)
    assert not isinstance(exc_info.value, CheckoutValidationError)
    assert exc_info.value.__cause__ is not None
    assert exc_info.value.__cause__.args[0] == "storage error"
    orders.insert.assert_called_once_with("o1", "c1", "PENDING", ANY)
    lines.insert.assert_not_called()
