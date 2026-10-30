from __future__ import annotations

import sqlite3


class OrderRepository:
    """Write access to the orders table; one header row per operation.

    Description:
        Repository for the orders table. Wraps one connection.
        The repository is write-only — it declares only the
        insert operation, no read-back.

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
        self._conn.row_factory = sqlite3.Row

    def insert(
        self,
        order_id: str,
        customer_id: str,
        status: str,
        created_at: str,
    ) -> None:
        """Insert one order header row.

        Description:
            Persist one order with the four header fields. Any
            storage rejection — including duplicate order_id —
            propagates unchanged.

        Steps:
            1. Persist one order row with the four header fields.
            2. Let any storage rejection propagate unchanged.
            3. Return None.
        """
        stmt = "INSERT INTO orders (order_id, customer_id, status, created_at) VALUES (?, ?, ?, ?)"
        self._conn.execute(stmt, (order_id, customer_id, status, created_at))
