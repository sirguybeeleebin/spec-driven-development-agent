def test_insert_writes_one_line() -> None:
    import sqlite3
    from pathlib import Path
    from repositories.order_lines import OrderLineRepository

    # Given
    conn = sqlite3.connect(":memory:")
    for path in sorted(Path("migrations").glob("*.sql")):
        conn.executescript(path.read_text())
    conn.execute("PRAGMA foreign_keys = ON")
    conn.commit()

    # Insert an order with id "o1"
    conn.execute(
        "INSERT INTO orders (order_id, customer_id, status, created_at) VALUES (?, ?, ?, ?)",
        ("o1", "c1", "pending", "2023-01-01T00:00:00Z"),
    )
    conn.commit()

    # Insert a product with id "p1"
    conn.execute(
        "INSERT INTO products (product_id, name, price_amount, price_currency, stock) VALUES (?, ?, ?, ?, ?)",
        ("p1", "Product 1", "10.00", "USD", 100),
    )
    conn.commit()

    # When
    repo = OrderLineRepository(conn)
    repo.insert("o1", "p1", 2, "2.00", "USD")

    # Then
    rows = conn.execute("SELECT order_id, product_id, qty FROM order_lines").fetchall()
    assert len(rows) == 1
    assert rows[0][0] == "o1"
    assert rows[0][1] == "p1"
    assert rows[0][2] == 2
def test_insert_duplicate_composite_key_raises() -> None:
    import sqlite3
    from pathlib import Path
    import pytest
    from repositories.order_lines import OrderLineRepository

    # Given
    conn = sqlite3.connect(":memory:")
    for path in sorted(Path("migrations").glob("*.sql")):
        conn.executescript(path.read_text())
    conn.execute("PRAGMA foreign_keys = ON")
    conn.commit()

    # Insert an order with id "o1"
    conn.execute(
        "INSERT INTO orders (order_id, customer_id, status, created_at) VALUES (?, ?, ?, ?)",
        ("o1", "c1", "pending", "2023-01-01T00:00:00Z"),
    )
    conn.commit()

    # Insert a product with id "p1"
    conn.execute(
        "INSERT INTO products (product_id, name, price_amount, price_currency, stock) VALUES (?, ?, ?, ?, ?)",
        ("p1", "Product 1", "10.00", "USD", 100),
    )
    conn.commit()

    # Insert a line for order "o1" and product "p1"
    repo = OrderLineRepository(conn)
    repo.insert("o1", "p1", 2, "2.00", "USD")

    # When & Then
    with pytest.raises(sqlite3.IntegrityError):
        repo.insert("o1", "p1", 3, "3.00", "USD")
def test_insert_with_unknown_reference_raises() -> None:
    import sqlite3
    from pathlib import Path
    import pytest
    from repositories.order_lines import OrderLineRepository

    # Given
    conn = sqlite3.connect(":memory:")
    for path in sorted(Path("migrations").glob("*.sql")):
        conn.executescript(path.read_text())
    conn.execute("PRAGMA foreign_keys = ON")
    conn.commit()

    # Insert a product with id "p1"
    conn.execute(
        "INSERT INTO products (product_id, name, price_amount, price_currency, stock) VALUES (?, ?, ?, ?, ?)",
        ("p1", "Product 1", "10.00", "USD", 100),
    )
    conn.commit()

    # When & Then
    with pytest.raises(sqlite3.IntegrityError):
        repo = OrderLineRepository(conn)
        repo.insert("o2", "p1", 2, "2.00", "USD")
