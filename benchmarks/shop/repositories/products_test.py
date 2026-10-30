def test_get_returns_product() -> None:
    import sqlite3
    from pathlib import Path
    from repositories.products import ProductRepository

    # Given
    conn = sqlite3.connect(":memory:")
    for path in sorted(Path("migrations").glob("*.sql")):
        conn.executescript(path.read_text())
    conn.execute("PRAGMA foreign_keys = ON")
    conn.commit()
    
    # Insert a product with id "p1", name "Pen", price "2.00" USD, stock 5
    conn.execute(
        "INSERT INTO products (product_id, name, price_amount, price_currency, stock) VALUES (?, ?, ?, ?, ?)",
        ("p1", "Pen", "2.00", "USD", 5)
    )
    conn.commit()
    
    # When
    repo = ProductRepository(conn)
    result = repo.get("p1")
    
    # Then
    assert result is not None
    assert len(result) == 5
    assert result["product_id"] == "p1"
    assert result["stock"] == 5
def test_get_missing_returns_none() -> None:
    import sqlite3
    from pathlib import Path
    from repositories.products import ProductRepository

    # Given
    conn = sqlite3.connect(":memory:")
    for path in sorted(Path("migrations").glob("*.sql")):
        conn.executescript(path.read_text())
    conn.execute("PRAGMA foreign_keys = ON")
    conn.commit()
    
    # When
    repo = ProductRepository(conn)
    result = repo.get("unknown-id")
    
    # Then
    assert result is None
