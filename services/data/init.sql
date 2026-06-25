CREATE SCHEMA IF NOT EXISTS cbp_sentry;
SET search_path TO cbp_sentry;

CREATE TABLE IF NOT EXISTS shipments (
    id TEXT PRIMARY KEY,
    manifest_id TEXT NOT NULL,
    shipper_name TEXT NOT NULL,
    consignee_name TEXT NOT NULL,
    origin_country TEXT NOT NULL,
    destination_country TEXT NOT NULL,
    hs_code TEXT,
    declared_value_usd DOUBLE PRECISION,
    declared_weight_kg DOUBLE PRECISION,
    description TEXT,
    vessel_name TEXT,
    vessel_imo TEXT,
    vessel_flag TEXT,
    dwell_days DOUBLE PRECISION,
    ais_stuffing_country TEXT,
    port_calls TEXT,
    element9_is_mismatch BOOLEAN DEFAULT FALSE,
    element9_confidence DOUBLE PRECISION,
    element9_declared_country TEXT,
    element9_actual_country TEXT,
    shipper_age_months INTEGER,
    shipper_country TEXT,
    consignee_country TEXT,
    ad_cvd_rate DOUBLE PRECISION,
    ad_cvd_applicable BOOLEAN DEFAULT FALSE,
    status TEXT DEFAULT 'received',
    risk_score DOUBLE PRECISION,
    risk_delta DOUBLE PRECISION DEFAULT 0,
    h1_score DOUBLE PRECISION,
    h2_score DOUBLE PRECISION,
    h3_score DOUBLE PRECISION,
    h1_h2_score DOUBLE PRECISION,
    last_polled_at TIMESTAMP,
    ofac_screened_at TIMESTAMP,
    ofac_match BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP,
    manifest_source_id TEXT,
    ship_id TEXT,
    calculated_risk_score DOUBLE PRECISION,
    risk_score_calculated_at TIMESTAMP,
    risk_score_breakdown TEXT,
    confidence_interval TEXT,
    model_version TEXT,
    model_maturity INTEGER DEFAULT 15,
    corridor_id TEXT,
    bill_of_lading TEXT,
    voyage_number TEXT,
    h2_signals TEXT,
    h3_recommendation TEXT,
    customs_flags TEXT,
    inspection_history TEXT,
    commodity_code TEXT,
    commodity_name TEXT,
    price_variance_percent DOUBLE PRECISION,
    unit_price_per_kg DOUBLE PRECISION,
    declared_unit_value DOUBLE PRECISION,
    audit_trail JSONB,
    risk_breakdown JSONB,
    ai_synthesis JSONB,
    isf_data JSONB,
    isf_element_mismatch BOOLEAN DEFAULT FALSE,
    isf_filed_date TIMESTAMP,
    isf_late_filing BOOLEAN DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS manifests (
    id TEXT PRIMARY KEY,
    filename TEXT NOT NULL,
    row_count INTEGER,
    extracted_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS upload_jobs (
    id TEXT PRIMARY KEY,
    filename TEXT NOT NULL,
    status TEXT DEFAULT 'pending',
    total_rows INTEGER DEFAULT 0,
    processed_rows INTEGER DEFAULT 0,
    inserted_rows INTEGER DEFAULT 0,
    duplicate_rows INTEGER DEFAULT 0,
    high_risk_count INTEGER DEFAULT 0,
    medium_risk_count INTEGER DEFAULT 0,
    low_risk_count INTEGER DEFAULT 0,
    error_count INTEGER DEFAULT 0,
    errors JSONB DEFAULT '[]'::jsonb,
    manifest_id TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS scores (
    id TEXT PRIMARY KEY,
    shipment_id TEXT NOT NULL REFERENCES shipments(id) ON DELETE CASCADE,
    h1_score DOUBLE PRECISION,
    h2_score DOUBLE PRECISION,
    h1_h2_score DOUBLE PRECISION,
    total_score DOUBLE PRECISION,
    components JSONB,
    xai_assertions JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS corridors (
    id TEXT PRIMARY KEY,
    display_name TEXT,
    origin_country TEXT,
    destination_country TEXT,
    risk_level TEXT DEFAULT 'MEDIUM',
    primary_hs_chapters TEXT,
    risk_profile TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    last_refreshed_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS corridor_duties (
    id SERIAL PRIMARY KEY,
    corridor_id TEXT REFERENCES corridors(id) ON DELETE CASCADE,
    case_number TEXT,
    duty_type TEXT,
    product_description TEXT,
    hs_prefix TEXT,
    rate_pct DOUBLE PRECISION,
    status TEXT DEFAULT 'ACTIVE',
    source_url TEXT,
    last_refreshed_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS enforcement_actions (
    id SERIAL PRIMARY KEY,
    corridor_id TEXT REFERENCES corridors(id) ON DELETE CASCADE,
    case_id TEXT,
    entity_name TEXT,
    case_status TEXT,
    case_year INTEGER,
    duty_evaded_usd DOUBLE PRECISION,
    source_description TEXT,
    source_url TEXT,
    last_refreshed_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS pre_manifest_vessels (
    vessel_imo TEXT PRIMARY KEY,
    vessel_name TEXT,
    mmsi TEXT,
    flag_state TEXT,
    origin_port TEXT,
    origin_country TEXT,
    destination_port TEXT,
    destination_country TEXT,
    corridor_id TEXT,
    eta_us TIMESTAMP,
    ais_status TEXT,
    current_lat DOUBLE PRECISION,
    current_lon DOUBLE PRECISION,
    speed_knots DOUBLE PRECISION,
    last_refreshed_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS weight_configurations (
    id TEXT PRIMARY KEY,
    corridor TEXT,
    w_corridor DOUBLE PRECISION NOT NULL,
    w_vessel DOUBLE PRECISION NOT NULL,
    w_manifest DOUBLE PRECISION NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP,
    created_by TEXT NOT NULL,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS scoring_overrides (
    id TEXT PRIMARY KEY,
    shipment_id TEXT NOT NULL REFERENCES shipments(id) ON DELETE CASCADE,
    original_score DOUBLE PRECISION NOT NULL,
    override_decision TEXT NOT NULL,
    feedback_type TEXT,
    analyst_id TEXT NOT NULL,
    analyst_name TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    notes TEXT
);

CREATE TABLE IF NOT EXISTS weight_suggestions (
    id TEXT PRIMARY KEY,
    corridor TEXT,
    affected_feature TEXT NOT NULL,
    suggested_value DOUBLE PRECISION NOT NULL,
    confidence_pct DOUBLE PRECISION NOT NULL,
    corroboration_count INTEGER NOT NULL,
    status TEXT DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT NOW(),
    reviewed_at TIMESTAMP,
    reviewed_by TEXT,
    rationale TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS shipment_line_items (
    id TEXT PRIMARY KEY,
    shipment_id TEXT NOT NULL REFERENCES shipments(id) ON DELETE CASCADE,
    line_number INTEGER NOT NULL,
    sku TEXT,
    product_description TEXT NOT NULL,
    quantity DOUBLE PRECISION NOT NULL,
    unit TEXT NOT NULL,
    unit_value_usd DOUBLE PRECISION NOT NULL,
    total_value_usd DOUBLE PRECISION NOT NULL,
    hs_code TEXT,
    data_source TEXT DEFAULT 'ISF-Element-1',
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS routing_events (
    id TEXT PRIMARY KEY,
    shipment_id TEXT NOT NULL REFERENCES shipments(id) ON DELETE CASCADE,
    event_type TEXT NOT NULL,
    location TEXT NOT NULL,
    event_date TIMESTAMP NOT NULL,
    notes TEXT,
    data_source TEXT DEFAULT 'AIS-Archive',
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS parties_involved (
    id TEXT PRIMARY KEY,
    shipment_id TEXT NOT NULL REFERENCES shipments(id) ON DELETE CASCADE,
    party_name TEXT NOT NULL,
    party_role TEXT NOT NULL,
    country TEXT NOT NULL,
    risk_note TEXT,
    data_source TEXT DEFAULT 'ISF-Filing',
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS entity_ownership_chain (
    id TEXT PRIMARY KEY,
    shipment_id TEXT NOT NULL REFERENCES shipments(id) ON DELETE CASCADE,
    tier_number INTEGER NOT NULL,
    entity_name TEXT NOT NULL,
    jurisdiction TEXT NOT NULL,
    matching_evidence TEXT NOT NULL,
    relationship_type TEXT,
    data_source TEXT DEFAULT 'Senzing-Trade-Graph',
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS historical_import_patterns (
    id TEXT PRIMARY KEY,
    shipment_id TEXT NOT NULL REFERENCES shipments(id) ON DELETE CASCADE,
    pattern_month TEXT NOT NULL,
    shipment_count INTEGER NOT NULL,
    total_weight_kg DOUBLE PRECISION NOT NULL,
    declared_origin TEXT NOT NULL,
    avg_unit_value_usd DOUBLE PRECISION NOT NULL,
    pattern_notes TEXT,
    data_source TEXT DEFAULT 'Trade-Flow-Analysis',
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS trade_flow_history (
    id TEXT PRIMARY KEY,
    shipment_id TEXT NOT NULL REFERENCES shipments(id) ON DELETE CASCADE,
    referenced_shipment_id TEXT,
    export_month TEXT NOT NULL,
    origin_country TEXT NOT NULL,
    export_port TEXT NOT NULL,
    transit_days INTEGER NOT NULL,
    quantity_kg DOUBLE PRECISION NOT NULL,
    unit_value_usd DOUBLE PRECISION NOT NULL,
    shipment_status TEXT NOT NULL,
    data_source TEXT DEFAULT 'Shipper-Consignee-History',
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS entity_relationships (
    id TEXT PRIMARY KEY,
    shipment_id TEXT NOT NULL REFERENCES shipments(id) ON DELETE CASCADE,
    entity_a_id TEXT NOT NULL,
    entity_a_name TEXT NOT NULL,
    entity_a_type TEXT NOT NULL,
    entity_b_id TEXT NOT NULL,
    entity_b_name TEXT NOT NULL,
    entity_b_type TEXT NOT NULL,
    relationship_type TEXT NOT NULL,
    confidence_score DOUBLE PRECISION,
    data_source TEXT DEFAULT 'Entity-Resolution',
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS risk_components (
    id TEXT PRIMARY KEY,
    shipment_id TEXT NOT NULL REFERENCES shipments(id) ON DELETE CASCADE,
    component_name TEXT NOT NULL,
    component_category TEXT NOT NULL,
    component_value DOUBLE PRECISION NOT NULL,
    component_max DOUBLE PRECISION NOT NULL,
    component_weight DOUBLE PRECISION NOT NULL,
    weighted_value DOUBLE PRECISION NOT NULL,
    evidence TEXT NOT NULL,
    data_source TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS risk_adjustments (
    id TEXT PRIMARY KEY,
    shipment_id TEXT NOT NULL REFERENCES shipments(id) ON DELETE CASCADE,
    adjustment_type TEXT NOT NULL,
    adjustment_name TEXT NOT NULL,
    adjustment_amount DOUBLE PRECISION NOT NULL,
    adjustment_multiplier DOUBLE PRECISION DEFAULT 1.0,
    confidence_score DOUBLE PRECISION NOT NULL,
    evidence_detail TEXT NOT NULL,
    data_source TEXT NOT NULL,
    applied_timestamp TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS risk_ledger (
    id TEXT PRIMARY KEY,
    shipment_id TEXT NOT NULL REFERENCES shipments(id) ON DELETE CASCADE,
    ledger_step INTEGER NOT NULL,
    step_name TEXT NOT NULL,
    step_description TEXT NOT NULL,
    input_value DOUBLE PRECISION,
    operation TEXT NOT NULL,
    output_value DOUBLE PRECISION NOT NULL,
    notes TEXT,
    data_source TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS risk_what_if_scenarios (
    id TEXT PRIMARY KEY,
    shipment_id TEXT NOT NULL REFERENCES shipments(id) ON DELETE CASCADE,
    scenario_name TEXT NOT NULL,
    scenario_description TEXT NOT NULL,
    scenario_priority TEXT DEFAULT 'MEDIUM',
    what_if_true_description TEXT NOT NULL,
    what_if_true_evidence_needed TEXT NOT NULL,
    what_if_true_risk_score DOUBLE PRECISION,
    what_if_false_description TEXT NOT NULL,
    what_if_false_evidence_needed TEXT NOT NULL,
    what_if_false_risk_score DOUBLE PRECISION,
    current_risk_score DOUBLE PRECISION NOT NULL,
    impact_if_true DOUBLE PRECISION,
    impact_if_false DOUBLE PRECISION,
    impact_category TEXT,
    investigation_recommendation TEXT,
    data_source TEXT DEFAULT 'Risk-Analysis-Engine',
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS risk_score_cache (
    id TEXT PRIMARY KEY,
    shipment_id TEXT UNIQUE NOT NULL REFERENCES shipments(id) ON DELETE CASCADE,
    final_score DOUBLE PRECISION NOT NULL,
    risk_level TEXT,
    confidence_interval DOUBLE PRECISION,
    breakdown_json JSONB NOT NULL,
    current_model_version TEXT NOT NULL,
    calculation_timestamp TIMESTAMP NOT NULL,
    is_stale BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS risk_score_transactions (
    id TEXT PRIMARY KEY,
    shipment_id TEXT NOT NULL REFERENCES shipments(id) ON DELETE CASCADE,
    previous_final_score DOUBLE PRECISION,
    new_final_score DOUBLE PRECISION NOT NULL,
    score_delta DOUBLE PRECISION,
    transaction_type TEXT NOT NULL,
    transaction_reason TEXT,
    previous_breakdown_json JSONB,
    new_breakdown_json JSONB NOT NULL,
    triggered_by TEXT,
    triggered_by_model_version TEXT,
    transaction_timestamp TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS model_versions (
    id TEXT PRIMARY KEY,
    model_name TEXT NOT NULL,
    version_number TEXT NOT NULL,
    training_date TIMESTAMP,
    released_at TIMESTAMP,
    isolation_forest_n_estimators INTEGER,
    isolation_forest_contamination DOUBLE PRECISION,
    isolation_forest_random_state INTEGER,
    lightgbm_num_leaves INTEGER,
    lightgbm_learning_rate DOUBLE PRECISION,
    lightgbm_max_depth INTEGER,
    is_active BOOLEAN DEFAULT FALSE,
    deprecated_at TIMESTAMP,
    total_calculations INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    notes TEXT
);

CREATE TABLE IF NOT EXISTS altana_scenarios (
    id TEXT PRIMARY KEY,
    shipment_id TEXT UNIQUE NOT NULL REFERENCES shipments(id) ON DELETE CASCADE,
    risk_score_id TEXT NOT NULL REFERENCES risk_score_cache(id) ON DELETE CASCADE,
    initial_score_before_altana DOUBLE PRECISION NOT NULL,
    threshold_met BOOLEAN,
    query_timestamp TIMESTAMP,
    altana_confidence DOUBLE PRECISION,
    altana_recommendation TEXT,
    altana_risk_factors JSONB,
    supply_chain_opacity DOUBLE PRECISION,
    sanctions_exposure BOOLEAN,
    confidence_bracket TEXT,
    adjustment_points DOUBLE PRECISION,
    final_score_after_altana DOUBLE PRECISION,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS eapa_cases (
    id TEXT PRIMARY KEY,
    entity_name TEXT NOT NULL,
    origin_country TEXT,
    destination_country TEXT,
    case_id TEXT,
    case_year INTEGER,
    duty_evaded_usd DOUBLE PRECISION,
    outcome TEXT,
    product_description TEXT,
    data_source TEXT DEFAULT 'EAPA-History',
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS comtrade_cache (
    id TEXT PRIMARY KEY,
    origin_country TEXT NOT NULL,
    destination_country TEXT NOT NULL,
    hs_chapter TEXT,
    year INTEGER NOT NULL,
    trade_value_usd DOUBLE PRECISION,
    unit_quantity DOUBLE PRECISION,
    unit_measure TEXT,
    fetched_at TIMESTAMP DEFAULT NOW(),
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(origin_country, destination_country, hs_chapter, year)
);

CREATE TABLE IF NOT EXISTS score_history (
    id SERIAL PRIMARY KEY,
    shipment_id TEXT NOT NULL REFERENCES shipments(id) ON DELETE CASCADE,
    score REAL,
    model_version TEXT,
    model_maturity INTEGER,
    scored_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_shipments_manifest_source_id ON shipments(manifest_source_id);
CREATE INDEX IF NOT EXISTS idx_shipments_origin_destination ON shipments(origin_country, destination_country);
CREATE INDEX IF NOT EXISTS idx_shipments_risk_score ON shipments(risk_score DESC);
CREATE INDEX IF NOT EXISTS idx_shipments_status ON shipments(status);
CREATE INDEX IF NOT EXISTS idx_risk_cache_shipment ON risk_score_cache(shipment_id);
CREATE INDEX IF NOT EXISTS idx_risk_txn_shipment ON risk_score_transactions(shipment_id);
CREATE INDEX IF NOT EXISTS idx_risk_txn_type ON risk_score_transactions(transaction_type);
CREATE INDEX IF NOT EXISTS idx_risk_txn_timestamp ON risk_score_transactions(transaction_timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_model_active ON model_versions(is_active);
CREATE INDEX IF NOT EXISTS idx_altana_shipment ON altana_scenarios(shipment_id);
CREATE INDEX IF NOT EXISTS idx_eapa_entity ON eapa_cases(entity_name);
CREATE INDEX IF NOT EXISTS idx_comtrade_corridor ON comtrade_cache(origin_country, destination_country);
CREATE INDEX IF NOT EXISTS idx_score_history_shipment ON score_history(shipment_id, scored_at DESC);

CREATE OR REPLACE VIEW corridor_enforcement_actions AS
SELECT * FROM enforcement_actions;

CREATE OR REPLACE VIEW manifest_upload_jobs AS
SELECT * FROM upload_jobs;

CREATE OR REPLACE VIEW risk_score_adjustments AS
SELECT * FROM risk_adjustments;

CREATE OR REPLACE VIEW risk_score_ledger AS
SELECT * FROM risk_ledger;

CREATE OR REPLACE VIEW risk_score_components AS
SELECT * FROM risk_components;

CREATE OR REPLACE VIEW risk_scores_cache AS
SELECT * FROM risk_score_cache;
