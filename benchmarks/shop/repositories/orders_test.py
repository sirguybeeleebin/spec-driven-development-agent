import sqlite3
from pathlib import Path

import pytest
from repositories.orders import OrderRepository


def test_insert_writes_header_row():
    conn = sqlite3.connect(":memory:")
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row

    for path in sorted(Path("migrations").glob("*.sql")):
        conn.executescript(path.read_text(encoding="utf-8"))

    sut = OrderRepository(conn=conn)
    sut.insert(
        order_id="o1",
        customer_id="c1",
        status="PENDING",
        created_at="2024-01-01T00:00:00+00:00",
    )

    rows = conn.execute("SELECT * FROM orders").fetchall()
    assert len(rows) == 1
    row = rows[0]
    assert row["order_id"] == "o1"
    assert row["status"] == "PENDING"
def test_insert_duplicate_raises():
    conn = sqlite3.connect(":memory:")
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row

    for path in sorted(Path("migrations").glob("*.sql")):
        conn.executescript(path.read_text(encoding="utf-8"))

    sut = OrderRepository(conn=conn)
    sut.insert(
        order_id="o1",
        customer_id="c1",
        status="PENDING",
        created_at="2024-01-01T00:00:00+00:00",
    )
    conn.commit()

    with pytest.raises(sqlite3.IntegrityError):
        sut.insert(
            order_id="o1",
            customer_id="c2",
            status="PENDING",
            created_at="2024-01-01T00:00:00+00:00",
        )
