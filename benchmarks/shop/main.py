from __future__ import annotations

import sqlite3
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Manage the application lifecycle.

    Description:
        Open one shared in-memory connection, apply the schema,
        build the three repositories, the checkout service, and
        the orders router on startup; close the connection on
        shutdown. The shutdown path runs even when startup fails
        after the connection was opened.

    Steps:
        1. On startup, open one shared connection to `:memory:`,
           configured so it can be used from any thread.
        2. Apply the schema to that connection.
        3. Build the three repositories over the connection.
        4. Build the checkout service over the three
           repositories.
        5. Attach exactly one router to the application, closed
           over the service.
        6. Yield control so the application serves requests.
        7. On shutdown, close the shared connection inside a
           finalizer that runs even when startup fails after the
           connection was opened.
        8. Let any storage error from connect or schema loading
           propagate unchanged. Let any framework error from
           startup propagate unchanged.
    """
    # Open one shared connection to :memory:, configured so it can be used from any thread.
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    try:
        # Apply the schema to that connection.
        with open("migrations/001_init.sql") as f:
            schema = f.read()
        conn.executescript(schema)

        # Build the three repositories over the connection.
        from repositories import OrderLineRepository, OrderRepository, ProductRepository
        product_repo = ProductRepository(conn)
        order_repo = OrderRepository(conn)
        order_line_repo = OrderLineRepository(conn)

        # Build the checkout service over the three repositories.
        from services import CheckoutService
        checkout_service = CheckoutService(product_repo, order_repo, order_line_repo)

        # Attach exactly one router to the application, closed over the service.
        from routers import make_orders_router
        orders_router = make_orders_router(checkout_service)
        app.include_router(orders_router)

        # Yield control so the application serves requests.
        yield

    finally:
        # On shutdown, close the shared connection inside a finalizer that runs even when startup fails after the connection was opened.
        conn.close()


app: FastAPI = FastAPI(
    title="Shop",
    version="0.1.0",
    lifespan=lifespan,
)
