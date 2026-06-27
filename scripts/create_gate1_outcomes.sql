-- Gate 1 investigation outcomes: the real Gate-2 training signal.
-- Officer triage (HOLD / EXAMINE / CLEAR) and confirmed disposition per shipment.
-- Maturity ladder advances toward Gate 2 when confirmed outcomes accumulate
-- (target: gate1_outcomes >= 200).
CREATE TABLE IF NOT EXISTS risk_scoring.gate1_outcomes (
    id              SERIAL PRIMARY KEY,
    shipment_id     TEXT NOT NULL,
    officer_action  TEXT NOT NULL,            -- HOLD | EXAMINE | CLEAR
    outcome         TEXT,                     -- confirmed | cleared | pending
    predicted_risk  DOUBLE PRECISION,
    analyst_id      TEXT,
    notes           TEXT,
    created_at      TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_gate1_outcomes_shipment ON risk_scoring.gate1_outcomes (shipment_id);
CREATE INDEX IF NOT EXISTS idx_gate1_outcomes_created ON risk_scoring.gate1_outcomes (created_at);

\echo '--- gate1_outcomes ready ---'
\d risk_scoring.gate1_outcomes
