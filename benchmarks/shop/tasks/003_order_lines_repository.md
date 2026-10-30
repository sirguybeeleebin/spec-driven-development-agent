# Task

- task_id: 003_order_lines_repository
- target: repositories/order_lines.py
- target_test: repositories/order_lines_test.py

# Goal

Define `OrderLineRepository` with `insert` — the only operation `CheckoutService` needs to persist one order line.

# Interfaces

```python
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
        ...

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
        ...
```

# Scenarios

## insert writes one line

```gherkin
Given an empty shop store with the schema applied
And an order with id "o1" and a product with id "p1" are persisted directly
When a line for order "o1" and product "p1" is inserted with qty 2 and unit "2.00" USD
Then the order_lines table contains one row for (order_id "o1", product_id "p1")
And that row's qty is 2
```

## insert duplicate composite key raises

```gherkin
Given an empty shop store with the schema applied
And an order with id "o1" and a product with id "p1" are persisted directly
And a line for order "o1" and product "p1" is inserted
When another line for the same order and product is inserted
Then the storage's integrity error is raised
```

## insert with unknown reference raises

```gherkin
Given an empty shop store with the schema applied
And a product with id "p1" is persisted directly
When a line is inserted for an order id that does not exist
Then the storage's referential integrity error is raised
```