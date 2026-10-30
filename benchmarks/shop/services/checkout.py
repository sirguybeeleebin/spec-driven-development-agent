from typing import Protocol, Callable


class ProductRepository(Protocol):
    """The product repository operations CheckoutService depends on.

    Description:
        Narrow structural contract for the product repository.
        Checkout only reads products — it never writes them — so
        this protocol declares only the lookup operation.

    Steps:
        1. Declare the get operation.
    """

    def get(self, product_id: str) -> dict | None:
        """Return the product with the given id, or None.

        Description:
            Look up one product by primary key. Missing rows are
            not an error. Checkout uses this to validate that
            every line references an existing product and to read
            its stock.

        Steps:
            1. Read the product row whose primary key equals
               product_id.
            2. Return the row as a mapping with exactly five
               keys — product_id, name, price_amount,
               price_currency, stock — or None.

        Returns:
            dict | None: A dict with exactly five keys, or None.
        """
        ...


class OrderRepository(Protocol):
    """The order header repository operations CheckoutService depends on.

    Description:
        Narrow structural contract for the order header
        repository. Checkout only writes the header — it never
        reads it back — so this protocol declares only the insert
        operation.

    Steps:
        1. Declare the insert operation.
    """

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
            constraint violation propagates unchanged.

        Steps:
            1. Persist one order row with the four header fields.
            2. Return None.

        Raises:
            sqlite3.IntegrityError: On duplicate order_id or any
                other constraint violation. Propagated unchanged.
        """
        ...


class OrderLineRepository(Protocol):
    """The order line repository operations CheckoutService depends on.

    Description:
        Narrow structural contract for the order line repository.
        Checkout only writes lines — it never reads them back —
        so this protocol declares only the insert operation.

    Steps:
        1. Declare the insert operation.
    """

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


class CheckoutService:
    """Turns a list of order lines into a persisted order; holds no connection and no clock of its own.

    Description:
        Service layer for checkout. Validates a list of order
        lines against product stock, then persists the order
        header and every line through the order and order-line
        repositories. The result is assembled from the values
        written, not read back from storage.

    Steps:
        1. Store the three injected repositories on the instance.
        2. Expose checkout.
    """

    def __init__(
        self,
        products: ProductRepository,
        orders: OrderRepository,
        lines: OrderLineRepository,
    ) -> None:
        """Wrap three repositories.

        Description:
            Store every dependency on the instance so checkout
            can delegate to them.

        Steps:
            1. Store the product repository on the instance.
            2. Store the order header repository on the instance.
            3. Store the order line repository on the instance.
            4. Return None.
        """
        self.products = products
        self.orders = orders
        self.lines = lines

    def checkout(
        self,
        lines: list[dict],
        customer_id: str,
        order_id: str,
        clock: Callable[[], str],
    ) -> dict:
        """Turn a list of order lines into a persisted order.

        Description:
            Validate the whole lines list before touching any
            repository, so a failure leaves the order store
            untouched. On success, persist the order header and
            every line, one write per repository call. Return a
            mapping assembled from the values written — order_id,
            customer_id, status "PENDING", created_at from the
            clock, and the input lines list.

        Steps:
            1. Reject an empty lines list as the first action,
               before any repository call.
            2. Look up every line's product through the product
               repository; a missing product is an error.
            3. Reject the request when any line's quantity
               exceeds its product's stock.
            4. Reject the request when any two lines in the input
               share the same product_id.
            5. Read created_at from the clock.
            6. Persist the order header through the order
               repository.
            7. Persist every line through the order line
               repository, in the input order.
            8. Return a dict with exactly five keys — order_id,
               customer_id, status "PENDING", created_at from
               step 5, lines from the input lines list.

        Returns:
            dict: A dict with exactly five keys — order_id,
                customer_id, status, created_at, lines — where
                status is "PENDING".

        Raises:
            ValueError: When the lines list is empty.
            ValueError: When any line references a missing product.
            ValueError: When any line's quantity exceeds its
                product's stock.
            ValueError: When two lines share the same product_id.
            sqlite3.IntegrityError: Whatever the order or order
                line repository raises when persisting.
        """
        # Step 1: Reject an empty lines list as the first action, before any repository call
        if not lines:
            raise ValueError("Lines list cannot be empty")

        # Step 2: Look up every line's product through the product repository; a missing product is an error
        product_map = {}
        line_product_ids = []
        for line in lines:
            product = self.products.get(line["product_id"])
            if product is None:
                raise ValueError(f"Product {line['product_id']} not found")
            product_map[line["product_id"]] = product
            line_product_ids.append(line["product_id"])

        # Step 3: Reject the request when any line's quantity exceeds its product's stock
        for line in lines:
            if line["qty"] > product_map[line["product_id"]]["stock"]:
                raise ValueError(
                    f"Line quantity {line['qty']} exceeds stock {product_map[line['product_id']]['stock']} for product {line['product_id']}"
                )

        # Step 4: Reject the request when any two lines in the input share the same product_id
        if len(line_product_ids) != len(set(line_product_ids)):
            raise ValueError("Duplicate product IDs in lines list")

        # Step 5: Read created_at from the clock
        created_at = clock()

        # Step 6: Persist the order header through the order repository
        self.orders.insert(order_id, customer_id, "PENDING", created_at)

        # Step 7: Persist every line through the order line repository, in the input order
        for line in lines:
            self.lines.insert(
                order_id,
                line["product_id"],
                line["qty"],
                line["unit_amount"],
                line["unit_currency"],
            )

        # Step 8: Return a dict with exactly five keys — order_id, customer_id, status "PENDING", created_at from step 5, lines from the input lines list
        return {
            "order_id": order_id,
            "customer_id": customer_id,
            "status": "PENDING",
            "created_at": created_at,
            "lines": lines,
        }
