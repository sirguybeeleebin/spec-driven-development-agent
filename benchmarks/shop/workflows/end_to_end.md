```mermaid
graph LR
    001_products_repository
    002_orders_repository
    003_order_lines_repository
    004_checkout_service
    005_orders_router
    006_main

    001_products_repository --> 003_order_lines_repository
    002_orders_repository --> 003_order_lines_repository
    001_products_repository --> 004_checkout_service
    002_orders_repository --> 004_checkout_service
    003_order_lines_repository --> 004_checkout_service
    004_checkout_service --> 005_orders_router
    005_orders_router --> 006_main
```