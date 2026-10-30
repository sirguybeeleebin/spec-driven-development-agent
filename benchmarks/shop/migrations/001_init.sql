CREATE TABLE IF NOT EXISTS products (
    product_id TEXT PRIMARY KEY,
    name TEXT,
    price_amount TEXT,
    price_currency TEXT,
    stock INTEGER
);

CREATE TABLE IF NOT EXISTS orders (
    order_id TEXT PRIMARY KEY,
    customer_id TEXT,
    status TEXT,
    created_at TEXT
);

CREATE TABLE IF NOT EXISTS order_lines (
    order_id TEXT,
    product_id TEXT,
    qty INTEGER,
    unit_amount TEXT,
    unit_currency TEXT,
    PRIMARY KEY (order_id, product_id),
    FOREIGN KEY (order_id) REFERENCES orders(order_id),
    FOREIGN KEY (product_id) REFERENCES products(product_id)
);