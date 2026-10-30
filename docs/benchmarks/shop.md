# Shop

FastAPI + Pydantic + SQLite, eight tasks ordered by dependency.

Source: [benchmarks/shop/](../../benchmarks/shop/)

[← back to benchmarks](../benchmarks.md) · [← back to README](../../README.md)

## Layout

```text
benchmarks/shop/
├── AGENT.md
├── AGENT.yaml
├── __init__.py
├── skills/
│   ├── fastapi-implementing/SKILL.md
│   ├── fastapi-testing/SKILL.md
│   ├── sqlite-implementing/SKILL.md
│   └── sqlite-testing/SKILL.md
├── tasks/
│   ├── 001_ddl.md
│   ├── 002_products_repository.md
│   ├── 003_orders_repository.md
│   ├── 004_products_service.md
│   ├── 005_checkout_service.md
│   ├── 006_products_router.md
│   ├── 007_orders_router.md
│   └── 008_main.md
└── workflows/
    └── end_to_end.md
```

## Tasks

| Id | Produces | Depends on |
|---|---|---|
| `001_ddl` | Schema (products, orders, order_lines) | — |
| `002_products_repository` | ProductRepository | `001_ddl` |
| `003_orders_repository` | OrderRepository | `001_ddl` |
| `004_products_service` | ProductService | `002_products_repository` |
| `005_checkout_service` | CheckoutService | `002_products_repository`, `003_orders_repository` |
| `006_products_router` | Products router | `004_products_service` |
| `007_orders_router` | Orders router | `005_checkout_service` |
| `008_main` | Application wiring | all of the above |

No separate cart layer — `CheckoutService` accepts order lines directly.

## Constitution (`AGENT.md`)

- **Stack** — Python 3.12+, SQLite, FastAPI, Pydantic v2.
- **Database** — mermaid ER diagram with `products`, `orders`, `order_lines`.
- **Commenting** — why-comments before blocks, no restating code.
- **Tracing** — every function starts with `print(f"[{__name__}] {symbol} {detail}")`.

## Running

```bash
cd benchmarks/shop
python ../../main.py run --workflow workflows/end_to_end.md --verbose
```

Exit code `0` when every task ended `DONE`.