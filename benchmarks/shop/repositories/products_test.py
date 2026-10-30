import sqlite3
from pathlib import Path

from repositories.products import ProductRepository


def test_get_returns_product():
    conn = sqlite3.connect(":memory:")
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    for path in sorted(Path("migrations").glob("*.sql")):
        conn.executescript(path.read_text(encoding="utf-8"))

    conn.execute(
        "INSERT INTO products (product_id, name, price_amount, price_currency, stock) VALUES (?, ?, ?, ?, ?)",
        ("p1", "Pen", "2.00", "USD", 5)
    )
    conn.commit()

    sut = ProductRepository(conn=conn)
    result = sut.get("p1")

    assert result is not None
    assert len(result) == 5
    assert result["product_id"] == "p1"
    assert result["stock"] == 5
def test_get_missing_returns_none():
    conn = sqlite3.connect(":memory:")
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    for path in sorted(Path("migrations").glob("*.sql")):
        conn.executescript(path.read_text(encoding="utf-8"))

    sut = ProductRepository(conn=conn)
    result = sut.get("p1")

    assert result is None
