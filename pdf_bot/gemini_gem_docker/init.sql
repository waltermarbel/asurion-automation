-- Gemini Gem v5.3 Database Schema

-- Ensure UUID generator is available
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- 1. POLICIES (Master list of insurance types)
CREATE TABLE IF NOT EXISTS policies (
    policy_id SERIAL PRIMARY KEY,
    policy_name TEXT NOT NULL,
    policy_short_name TEXT NOT NULL UNIQUE,
    is_globally_active BOOLEAN DEFAULT TRUE
);

-- 2. POLICY RULES (Deductibles and prioritization per category)
CREATE TABLE IF NOT EXISTS policy_rules (
    policy_rule_id SERIAL PRIMARY KEY,
    policy_id INTEGER REFERENCES policies(policy_id),
    device_category TEXT NOT NULL,
    deductible_amount NUMERIC NOT NULL,
    is_adh_covered BOOLEAN DEFAULT FALSE,
    priority_for_tie_break INTEGER NOT NULL
);

-- 3. DEVICES (Inventory ledger)
CREATE TABLE IF NOT EXISTS devices (
    device_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    brand TEXT,
    model TEXT,
    serial_number TEXT UNIQUE,
    category TEXT,
    scanlily_url TEXT,
    retail_price_estimate NUMERIC,
    status TEXT DEFAULT 'INGESTED', -- INGESTED | VALUATED | MANUAL_REVIEW | CLAIM_READY
    created_at TIMESTAMP DEFAULT NOW()
);

-- 4. CLAIMS (Execution ledger)
CREATE TABLE IF NOT EXISTS claims (
    claim_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    device_id UUID REFERENCES devices(device_id),
    target_policy_id INTEGER REFERENCES policies(policy_id),
    status TEXT NOT NULL, -- PROCESSING | PDF_GENERATED | FAILED | SUBMITTED | DRY_RUN_COMPLETE
    failure_date DATE,
    failure_description TEXT,
    payout_estimate NUMERIC,
    generated_pdf_filename TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 5. SYSTEM LOG (Forensic audit trail)
CREATE TABLE IF NOT EXISTS system_log (
    log_id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP DEFAULT NOW(),
    actor TEXT,
    action TEXT,
    details JSONB
);

-- Helpful indexes for hot paths
CREATE INDEX IF NOT EXISTS idx_devices_status ON devices(status);
CREATE INDEX IF NOT EXISTS idx_devices_price_null ON devices(retail_price_estimate);
CREATE INDEX IF NOT EXISTS idx_claims_device_id ON claims(device_id);

-- Seed baseline policies (idempotent)
INSERT INTO policies (policy_name, policy_short_name)
VALUES
    ('Asurion Home+', 'AH'),
    ('Verizon Home Device Protect', 'VZ'),
    ('Protection 360', 'P360')
ON CONFLICT (policy_short_name) DO NOTHING;
