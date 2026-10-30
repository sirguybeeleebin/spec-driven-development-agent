import sqlite3
from pathlib import Path

import pytest
from repositories.order_lines import OrderLineRepository


def test_insert_writes_one_line():
    conn = sqlite3.connect(":memory:")
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    for path in sorted(Path("migrations").glob("*.sql")):
        conn.executescript(path.read_text(encoding="utf-8"))

    conn.execute("INSERT INTO orders (order_id, customer_id, status, created_at) VALUES (?, ?, ?, ?)", ("o1", "c1", "pending", "2023-01-01"))
    conn.execute("INSERT INTO products (product_id, name, price_amount, price_currency, stock) VALUES (?, ?, ?, ?, ?)", ("p1", "Product 1", "10.00", "USD", 100))
    conn.commit()

    sut = OrderLineRepository(conn=conn)
    sut.insert("o1", "p1", 2, "2.00", "USD")

    rows = conn.execute("SELECT * FROM order_lines").fetchall()
    assert len(rows) == 1
    row = rows[0]
    assert row["order_id"] == "o1"
    assert row["product_id"] == "p1"
    assert row["qty"] == 2
def test_insert_duplicate_composite_key_raises():
    conn = sqlite3.connect(":memory:")
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    for path in sorted(Path("migrations").glob("*.sql")):
        conn.executescript(path.read_text(encoding="utf-8"))

    conn.execute("INSERT INTO orders (order_id, customer_id, status, created_at) VALUES (?, ?, ?, ?)", ("o1", "c1", "pending", "2023-01-01"))
    conn.execute("INSERT INTO products (product_id, name, price_amount, price_currency, stock) VALUES (?, ?, ?, ?, ?)", ("p1", "Product 1", "10.00", "USD", 100))
    conn.commit()

    sut = OrderLineRepository(conn=conn)
    sut.insert("o1", "p1", 2, "2.00", "USD")

    with pytest.raises(sqlite3.IntegrityError):
        sut.insert("o1", "p1", 3, "3.00", "USD")
def test_insert_with_unknown_reference_raises():
    conn = sqlite3.connect(":memory:")
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    for path in sorted(Path("migrations").glob("*.sql")):
        conn.executescript(path.read_text(encoding="utf-8"))

    conn.execute("INSERT INTO products (product_id, name, price_amount, price_currency, stock) VALUES (?, ?, ?, ?, ?)", ("p1", "Product 1", "10.00", "USD", 100))
    conn.commit()

    sut = OrderLineRepository(conn=conn)
    with pytest.raises(sqlite3.IntegrityError):
        sut.insert("o1", "p1", 2, "2.00", "USD")
