def test_checkout_persists_order_and_lines() -> None:
    from unittest.mock import MagicMock
    from services.checkout import CheckoutService

    # Given
    product_repo = MagicMock()
    order_repo = MagicMock()
    line_repo = MagicMock()
    
    checkout_service = CheckoutService(product_repo, order_repo, line_repo)
    
    # Configure product repo to return a product with stock 10
    product_repo.get.return_value = {
        "product_id": "p1",
        "name": "Product 1",
        "price_amount": "10.00",
        "price_currency": "USD",
        "stock": 10
    }
    
    # Configure clock
    clock = MagicMock(return_value="2024-01-01T00:00:00+00:00")
    
    # When
    result = checkout_service.checkout(
        lines=[{
            "product_id": "p1",
            "qty": 1,
            "unit_amount": "10.00",
            "unit_currency": "USD"
        }],
        customer_id="c1",
        order_id="o1",
        clock=clock
    )
    
    # Then
    # Check returned mapping has exactly five keys
    assert len(result) == 5
    assert "order_id" in result
    assert "customer_id" in result
    assert "status" in result
    assert "created_at" in result
    assert "lines" in result
    
    # Check status is "PENDING"
    assert result["status"] == "PENDING"
    
    # Check created_at is correct
    assert result["created_at"] == "2024-01-01T00:00:00+00:00"
    
    # Check lines have one element for product "p1"
    assert len(result["lines"]) == 1
    assert result["lines"][0]["product_id"] == "p1"
    
    # Check order header is persisted
    order_repo.insert.assert_called_once_with(
        "o1",
        "c1",
        "PENDING",
        "2024-01-01T00:00:00+00:00"
    )
    
    # Check line is persisted under order "o1" with correct qty and amounts
    line_repo.insert.assert_called_once_with(
        "o1",
        "p1",
        1,
        "10.00",
        "USD"
    )
