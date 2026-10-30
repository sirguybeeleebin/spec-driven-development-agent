import sqlite3


class OrderLineRepository:
    """Write access to the order_lines table; one line row per operation.

    Description:
        Repository for the order_lines table. Wraps one
        connection. Checkout only writes lines — it never reads
        them back — so this repository declares only the insert
        operation.

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
        self.conn = conn

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
            constraint violation propagates unchanged.

        Steps:
            1. Persist one line row with the five fields.
            2. Return None.

        Raises:
            sqlite3.IntegrityError: On duplicate (order_id,
                product_id), on unknown order_id, on unknown
                product_id, or any other constraint violation.
                Propagated unchanged.
        """
        self.conn.execute(
            "INSERT INTO order_lines (order_id, product_id, qty, unit_amount, unit_currency) VALUES (?, ?, ?, ?, ?)",
            (order_id, product_id, qty, unit_amount, unit_currency),
        )
