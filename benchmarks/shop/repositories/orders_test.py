def test_insert_writes_header_row() -> None:
    import sqlite3
    from pathlib import Path
    from repositories.orders import OrderRepository

    # Given
    conn = sqlite3.connect(":memory:")
    for path in sorted(Path("migrations").glob("*.sql")):
        conn.executescript(path.read_text())
    conn.execute("PRAGMA foreign_keys = ON")
    conn.commit()

    # When
    repo = OrderRepository(conn)
    repo.insert(
        order_id="o1",
        customer_id="c1",
        status="PENDING",
        created_at="2024-01-01T00:00:00+00:00",
    )

    # Then
    rows = conn.execute("SELECT order_id, status FROM orders").fetchall()
    assert len(rows) == 1
    assert rows[0][0] == "o1"
    assert rows[0][1] == "PENDING"
def test_insert_duplicate_raises() -> None:
    import sqlite3
    from pathlib import Path
    import pytest
    from repositories.orders import OrderRepository

    # Given
    conn = sqlite3.connect(":memory:")
    for path in sorted(Path("migrations").glob("*.sql")):
        conn.executescript(path.read_text())
    conn.execute("PRAGMA foreign_keys = ON")
    conn.commit()

    repo = OrderRepository(conn)
    repo.insert(
        order_id="o1",
        customer_id="c1",
        status="PENDING",
        created_at="2024-01-01T00:00:00+00:00",
    )

    # When & Then
    with pytest.raises(sqlite3.IntegrityError):
        repo.insert(
            order_id="o1",
            customer_id="c2",
            status="PENDING",
            created_at="2024-01-01T00:00:00+00:00",
        )
