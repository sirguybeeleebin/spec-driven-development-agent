# Task

- task_id: 001_products_repository
- target_file: repositories/products.py
- target_test_file: repositories/products_test.py

# Goal

Read a product row by primary key, returning a mapping with exactly five keys or None.

# Declares

- ProductRepository

# Interfaces

```python
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
        ...

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
        ...
```

# Gherkins

## ProductRepository: get returns product

```gherkin
Given an empty product store with the schema applied
And a product with id "p1", name "Pen", price "2.00" USD, stock 5 is inserted directly
When the product with id "p1" is looked up
Then the result has exactly five keys
And its product_id is "p1"
And its stock is 5
```

## ProductRepository: get missing returns none

```gherkin
Given an empty product store with the schema applied
When the product with an unknown id is looked up
Then the result is none
```