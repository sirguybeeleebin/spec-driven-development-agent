from __future__ import annotations

import sqlite3


class OrderLineRepository:
    """Write access to the order_lines table; one line row per operation.

    Description:
        Repository for the order_lines table. Wraps one
        connection. The repository is write-only — it declares
        only the insert operation, no read-back.

    Steps:
        1. Store the connection on the instance.
        2. Expose insert.
    """

    def __init__(self, conn: sqlite3.Connection) -> None:
        """Wrap a storage connection.

        Description:
            Store the connection on the instance.

        Steps:
            1. Store the connection on the instance.
            2. Return None.
        """
        self._conn = conn

    def insert(
        self,
        order_id: str,
        product_id: str,
        qty: int,
        unit_amount: str,
        unit_currency: str,
    ) -> None:
        """Insert one order line row.

        Description:
            Persist one line associated with the given order. Any
            storage rejection propagates unchanged.

        Steps:
            1. Persist one line row with the five fields.
            2. Let any storage rejection propagate unchanged.
            3. Return None.
        """
        stmt = "INSERT INTO order_lines (order_id, product_id, qty, unit_amount, unit_currency) VALUES (?, ?, ?, ?, ?)"
        self._conn.execute(stmt, (order_id, product_id, qty, unit_amount, unit_currency))
