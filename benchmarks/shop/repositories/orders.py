import sqlite3


class OrderRepository:
    """Write access to the orders table; one header row per operation.

    Description:
        Repository for the orders table. Wraps one connection.
        Checkout only writes the header — it never reads it
        back — so this repository declares only the insert
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
        customer_id: str,
        status: str,
        created_at: str,
    ) -> None:
        """Insert one order header row.

        Description:
            Persist one order with the four header fields. Any
            constraint violation — including duplicate order_id —
            propagates unchanged.

        Steps:
            1. Persist one order row with the four header fields.
            2. Return None.

        Raises:
            sqlite3.IntegrityError: On duplicate order_id or any
                other constraint violation. Propagated unchanged.
        """
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT INTO orders (order_id, customer_id, status, created_at) VALUES (?, ?, ?, ?)",
            (order_id, customer_id, status, created_at),
        )
