from __future__ import annotations

from enum import StrEnum

from fastapi import APIRouter, status
from fastapi.exceptions import HTTPException
from pydantic import BaseModel, ConfigDict, Field
from services.checkout import CheckoutStorageError, CheckoutValidationError


class OrderStatus(StrEnum):
    """Lifecycle status of an order; closed set of four allowed values.

    Description:
        Closed enumeration of the four allowed order statuses.
        The wire form of each value is the plain string of its
        name in upper case.
    """

    PENDING = "PENDING"
    PAID = "PAID"
    SHIPPED = "SHIPPED"
    CANCELLED = "CANCELLED"
class OrderLine(BaseModel):
    """Response model for one order line; immutable, closed to unknown fields.

    Description:
        Response shape of one order line. Carries four fields:
        product_id, qty, unit_amount, unit_currency. Immutable
        after construction. Closed to unknown fields. Also used
        as the request-model line shape.

    Steps:
        1. Declare four fields: product_id, qty, unit_amount,
           unit_currency.
        2. qty is constrained to be strictly positive.
        3. Reject unknown fields on construction.
        4. Freeze instances after construction.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    product_id: str = Field(
        ...,
        title="Product ID",
        description="Identifier of the product this line references.",
    )
    qty: int = Field(
        ...,
        gt=0,
        title="Quantity",
        description="Number of units of the product; strictly positive.",
    )
    unit_amount: str = Field(
        ...,
        title="Unit amount",
        description="Price amount per unit, as a decimal string.",
    )
    unit_currency: str = Field(
        ...,
        title="Unit currency",
        description="Currency code of the unit amount, e.g. USD.",
    )
class Order(BaseModel):
    """Response model for one order; immutable, closed to unknown fields.

    Description:
        Response shape of one order. Carries five fields:
        order_id, customer_id, status, created_at, lines.
        status is typed as OrderStatus. lines is a list of
        OrderLine. Immutable after construction. Closed to
        unknown fields.

    Steps:
        1. Declare five fields: order_id, customer_id, status,
           created_at, lines.
        2. Type status as OrderStatus.
        3. Type lines as a list of OrderLine.
        4. Reject unknown fields on construction.
        5. Freeze instances after construction.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    order_id: str = Field(
        ...,
        title="Order ID",
        description="Identifier of the persisted order.",
    )
    customer_id: str = Field(
        ...,
        title="Customer ID",
        description="Identifier of the customer who placed the order.",
    )
    status: OrderStatus = Field(
        ...,
        title="Status",
        description="Lifecycle status of the order.",
    )
    created_at: str = Field(
        ...,
        title="Created at",
        description="ISO-8601 timestamp of the moment the order was persisted.",
    )
    lines: list[OrderLine] = Field(
        ...,
        title="Lines",
        description="Order lines persisted with this order, in input order.",
    )
class OrderCreate(BaseModel):
    """Request body for creating an order; carries only what the client chooses.

    Description:
        Request shape accepted by the create endpoint. Carries
        three fields: customer_id, order_id, lines. status and
        created_at are absent — the service sets them, not the
        client. Closed to unknown fields.

    Steps:
        1. Declare three fields: customer_id, order_id, lines.
        2. Type lines as a list of OrderLine.
        3. Reject unknown fields on construction.
    """

    model_config = ConfigDict(extra="forbid")

    customer_id: str = Field(
        ...,
        title="Customer ID",
        description="Identifier of the customer placing the order.",
    )
    order_id: str = Field(
        ...,
        title="Order ID",
        description="Identifier the caller assigns to the new order.",
    )
    lines: list[OrderLine] = Field(
        ...,
        title="Lines",
        description="Order lines to persist with this order, in the order given.",
    )
def make_orders_router(
    service: CheckoutService,
) -> APIRouter:
    """Build the orders router closed over the given checkout service.

    Description:
        Register one create endpoint at POST / with prefix
        /orders and tag orders. Dispatch on the exception
        class, never on the exception message text:
        CheckoutValidationError maps to 400 Bad Request,
        CheckoutStorageError maps to 409 Conflict, any other
        exception propagates to FastAPI's default 500 handler.
        Success maps to 201 Created. Every HTTP status code is
        a named constant from ``fastapi.status``. The two
        exception classes are not declared in this file; they
        are imported from the module that owns the checkout
        service.

    Steps:
        1. Import CheckoutValidationError and CheckoutStorageError
           from the module that owns the checkout service; do
           not declare them in this file.
        2. Create the router with prefix /orders and tag
           orders.
        3. Register POST / . Input is OrderCreate; output is
           Order; success returns 201 Created.
        4. In the handler, convert ``OrderCreate.lines`` to a
           list of dicts and call ``service.checkout(...)``.
        5. Catch CheckoutValidationError and raise
           ``HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
           detail=str(exc)) from exc``. Do not inspect
           ``str(exc)`` to decide the status — the class alone
           decides.
        6. Catch CheckoutStorageError and raise
           ``HTTPException(status_code=status.HTTP_409_CONFLICT,
           detail=str(exc)) from exc``. Do not inspect
           ``str(exc)`` to decide the status — the class alone
           decides.
        7. Do not catch any other exception. Unexpected
           failures propagate to FastAPI's default 500 handler.
        8. Return the router.

    Returns:
        APIRouter: A router with the create endpoint
            registered.
    """
    router = APIRouter(prefix="/orders", tags=["orders"])

    @router.post("/", response_model=Order, status_code=status.HTTP_201_CREATED)
    def create(payload: OrderCreate) -> Order:
        lines = [
            {
                "product_id": line.product_id,
                "qty": line.qty,
                "unit_amount": line.unit_amount,
                "unit_currency": line.unit_currency,
            }
            for line in payload.lines
        ]
        try:
            result = service.checkout(
                lines=lines,
                customer_id=payload.customer_id,
                order_id=payload.order_id,
            )
        except CheckoutValidationError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(exc),
            ) from exc
        except CheckoutStorageError as exc:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=str(exc),
            ) from exc
        return Order(**result)

    return router
