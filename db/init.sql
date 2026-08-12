CREATE TABLE IF NOT EXISTS inventory (
    id          SERIAL PRIMARY KEY,
    sku         TEXT NOT NULL UNIQUE,
    name        TEXT NOT NULL,
    quantity    INTEGER NOT NULL DEFAULT 0 CHECK (quantity >= 0),
    unit_price  NUMERIC(10,2) NOT NULL CHECK (unit_price >= 0),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

INSERT INTO inventory (sku, name, quantity, unit_price) VALUES
    ('WIDGET-001', 'Standard Widget',     150, 4.99),
    ('WIDGET-002', 'Heavy-Duty Widget',    42, 12.50),
    ('GADGET-100', 'Basic Gadget',         88, 9.75),
    ('GADGET-200', 'Premium Gadget',       17, 29.99),
    ('SPROCKET-A', 'Sprocket Type A',     230, 1.25),
    ('SPROCKET-B', 'Sprocket Type B',     195, 1.75)
ON CONFLICT (sku) DO NOTHING;
