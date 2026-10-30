from __future__ import annotations

import sqlite3


class ProductRepository:
    """Read access to the products table; wraps one open storage connection.

    Description:
        Repository for the products table. Wraps a single
        connection, configures it to return rows as mappings,
        and exposes get. The repository is read-only — it
        declares only the lookup operation.

    Steps:
        1. Store the connection on the instance.
        2. Configure the connection so every fetched row is a
           mapping keyed by column name.
        3. Expose get.
    """

    def __init__(self, conn: sqlite3.Connection) -> None:
        """Wrap a storage connection.

        Description:
            Store the connection on the instance and configure it
            so every fetched row is a mapping keyed by column name,
            not a positional tuple.

        Steps:
            1. Store the connection on the instance.
            2. Configure the connection to return rows as mappings.
            3. Return None.
        """
        self._conn = conn
        self._conn.row_factory = sqlite3.Row

    def get(self, product_id: str) -> dict | None:
        """Return the product with the given id, or None.

        Description:
            Look up one product by primary key. A missing row is
            a valid outcome, not an error — return None when no
            product matches product_id.

        Steps:
            1. Look up the product whose primary key equals
               product_id.
            2. If no product matched, return None.
            3. Otherwise return the matched product as a mapping
               with exactly five keys: product_id, name,
               price_amount, price_currency, stock.

        Returns:
            dict | None: A dict with exactly five keys —
                product_id, name, price_amount, price_currency,
                stock — or None if no product matches product_id.
        """
        stmt = "SELECT product_id, name, price_amount, price_currency, stock FROM products WHERE product_id = ?"
        row = self._conn.execute(stmt, (product_id,)).fetchone()
        if row is None:
            return None
        return dict(row)
