-- 1. POLICIES MASTER TABLE
CREATE TABLE policies (
    policy_id SERIAL PRIMARY KEY,
    policy_name TEXT NOT NULL, -- e.g., "Asurion Home+"
    policy_short_name TEXT NOT NULL UNIQUE, -- e.g., "AH"
    is_globally_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 2. POLICY RULES (The Strategy)
CREATE TABLE policy_rules (
    policy_rule_id SERIAL PRIMARY KEY,
    policy_id INTEGER REFERENCES policies(policy_id),
    device_category TEXT NOT NULL, -- e.g., "Laptop"
    deductible_amount NUMERIC NOT NULL,
    is_adh_covered BOOLEAN DEFAULT FALSE,
    priority_for_tie_break INTEGER NOT NULL -- Lower is better
);

-- 3. DEVICES (The Inventory)
CREATE TABLE devices (
    device_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    brand TEXT,
    model TEXT,
    serial_number TEXT,
    category TEXT,
    scanlily_url TEXT,
    retail_price_estimate NUMERIC, -- The "Target" value
    retail_price_confidence FLOAT,
    status TEXT DEFAULT 'INGESTED', -- INGESTED, PROCESSED, CLAIMED
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 4. CLAIMS (The Execution)
CREATE TABLE claims (
    claim_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    device_id UUID REFERENCES devices(device_id),
    target_policy_id INTEGER REFERENCES policies(policy_id),
    status TEXT NOT NULL, -- SYSTEM_READY_TO_FILE, USER_SUBMITTED, CLOSED_PAID
    failure_date DATE,
    failure_description TEXT,
    payout_estimate NUMERIC,
    generated_pdf_url TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 5. AUDIT TRAIL (Forensic Integrity)
CREATE TABLE system_log (
    log_id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    actor TEXT, -- e.g., "PDF_BOT"
    action TEXT, -- e.g., "GENERATED_PDF"
    details JSONB
);

-- SEED DATA (Default Policies)
INSERT INTO policies (policy_name, policy_short_name) VALUES
('Asurion Home+', 'AH'),
('Verizon Home Device Protect', 'VZ'),
('Protection 360', 'P360');
