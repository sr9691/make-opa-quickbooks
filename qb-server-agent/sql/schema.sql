CREATE TABLE IF NOT EXISTS  transactions (
    transaction_id TEXT PRIMARY KEY,
    identifier TEXT,
    idempotency_key TEXT UNIQUE,
    timestamp DATETIME,
    status TEXT, -- 'pending', 'success', 'error', 'duplicate'
    processing_time_ms INTEGER,
    qbxml_request TEXT,
    qbxml_response TEXT,
    error_message TEXT,
    error_code TEXT,
    retry_count INTEGER DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_idempotency ON transactions(idempotency_key);
CREATE INDEX IF NOT EXISTS idx_timestamp ON transactions(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_status ON transactions(status);