PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY, name TEXT NOT NULL, preferred_fit TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY, name TEXT NOT NULL,
    category TEXT NOT NULL CHECK(category IN ('상의','아우터','하의')),
    subcategory TEXT NOT NULL, price INTEGER NOT NULL CHECK(price >= 0),
    description TEXT NOT NULL, color TEXT NOT NULL, sizes TEXT NOT NULL,
    measurements TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id),
    product_id INTEGER NOT NULL REFERENCES products(id), size TEXT NOT NULL,
    ordered_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS returns (
    id INTEGER PRIMARY KEY, order_id INTEGER NOT NULL UNIQUE REFERENCES orders(id),
    reason TEXT NOT NULL, returned_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS reviews (
    id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id),
    product_id INTEGER NOT NULL REFERENCES products(id), size TEXT NOT NULL,
    rating INTEGER NOT NULL CHECK(rating BETWEEN 1 AND 5),
    content TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS review_analysis (
    id INTEGER PRIMARY KEY,
    product_id INTEGER NOT NULL REFERENCES products(id),
    mode TEXT NOT NULL,
    result_json TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    UNIQUE(product_id, mode)
);
CREATE TABLE IF NOT EXISTS agent_logs (
    id INTEGER PRIMARY KEY, request_id TEXT NOT NULL,
    agent_type TEXT NOT NULL CHECK(agent_type IN ('review','fit')),
    product_id INTEGER REFERENCES products(id), user_id INTEGER REFERENCES users(id),
    size TEXT, status TEXT NOT NULL CHECK(status IN ('success','error')),
    processing_ms REAL NOT NULL, result_json TEXT, error_type TEXT,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);
CREATE TABLE IF NOT EXISTS resource_logs (
    id INTEGER PRIMARY KEY, request_id TEXT NOT NULL UNIQUE,
    operation TEXT NOT NULL CHECK(operation IN ('browse','review','fit')),
    cpu_percent REAL NOT NULL, cpu_ms REAL NOT NULL,
    memory_before_mb REAL NOT NULL, memory_after_mb REAL NOT NULL,
    memory_delta_mb REAL NOT NULL, processing_ms REAL NOT NULL,
    response_ms REAL NOT NULL, status TEXT NOT NULL CHECK(status IN ('success','error')),
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);
CREATE INDEX IF NOT EXISTS idx_orders_product_size ON orders(product_id, size);
CREATE INDEX IF NOT EXISTS idx_orders_user ON orders(user_id);
CREATE INDEX IF NOT EXISTS idx_reviews_product ON reviews(product_id);
CREATE INDEX IF NOT EXISTS idx_review_analysis_product ON review_analysis(product_id);
CREATE INDEX IF NOT EXISTS idx_agents_request ON agent_logs(request_id);
CREATE INDEX IF NOT EXISTS idx_resources_operation ON resource_logs(operation);
