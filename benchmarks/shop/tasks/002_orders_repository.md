# Task

- task_id: 002_orders_repository
- target: repositories/orders.py
- target_test: repositories/orders_test.py

# Goal

Define `OrderRepository` with `insert` — the only operation `CheckoutService` needs to persist the order header.

# Interfaces

```python
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
        ...

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
        ...
```

# Scenarios

## insert writes header row

```gherkin
Given an empty shop store with the schema applied
When an order with id "o1", customer "c1", status "PENDING", created at "2024-01-01T00:00:00+00:00" is inserted
Then the orders table contains one row with order_id "o1"
And that row's status is "PENDING"
```

## insert duplicate raises

```gherkin
Given an empty shop store with the schema applied
And an order with id "o1" is inserted
When another order with the same id "o1" is inserted
Then the storage's integrity error is raised
```