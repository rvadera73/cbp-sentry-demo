-- ============================================================================
-- CBP Sentry: Risk Scoring Schema (Phase 1)
-- ============================================================================
-- Creates the risk_scoring schema with 12 tables for model management,
-- scoring, and monitoring. Supports 7-factor engine with 3 gates and rules.
-- ============================================================================

-- Create schema
CREATE SCHEMA IF NOT EXISTS risk_scoring;

-- ============================================================================
-- Table 1: domains
-- ============================================================================
-- Represents risk domains (e.g., CBP, Sanction, Adverse, Shipping)
CREATE TABLE risk_scoring.domains (
    domain_id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_domains_name ON risk_scoring.domains(name);


-- ============================================================================
-- Table 2: scorecards
-- ============================================================================
-- Defines scoring rules, factors, and thresholds per domain
CREATE TABLE risk_scoring.scorecards (
    scorecard_id SERIAL PRIMARY KEY,
    domain_id INTEGER NOT NULL REFERENCES risk_scoring.domains(domain_id),
    factors JSONB NOT NULL,  -- 7 factors: {factor_name: weight, ...}
    rules JSONB NOT NULL,    -- 3 gates: {gate_id: [rule_ids], ...}
    thresholds JSONB NOT NULL,  -- Gate thresholds: {gate_id: threshold, ...}
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(domain_id)
);

CREATE INDEX idx_scorecards_domain ON risk_scoring.scorecards(domain_id);


-- ============================================================================
-- Table 3: features_cbp
-- ============================================================================
-- Feature catalog for the CBP domain
CREATE TABLE risk_scoring.features_cbp (
    feature_id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    description TEXT,
    type VARCHAR(50) NOT NULL,  -- 'categorical', 'numerical', 'temporal'
    data_type VARCHAR(50) NOT NULL,  -- 'integer', 'float', 'string', 'date'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_features_cbp_name ON risk_scoring.features_cbp(name);
CREATE INDEX idx_features_cbp_type ON risk_scoring.features_cbp(type);


-- ============================================================================
-- Table 4: rule_parameters (SCD Type 2)
-- ============================================================================
-- Slowly Changing Dimension Type 2: tracks parameter changes over time
CREATE TABLE risk_scoring.rule_parameters (
    parameter_id SERIAL PRIMARY KEY,
    rule_id INTEGER NOT NULL,
    parameter_name VARCHAR(255) NOT NULL,
    parameter_value TEXT NOT NULL,
    valid_from TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    valid_to TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT rule_params_temporal CHECK (valid_to IS NULL OR valid_to > valid_from)
);

CREATE INDEX idx_rule_parameters_rule_id ON risk_scoring.rule_parameters(rule_id);
CREATE INDEX idx_rule_parameters_valid_from ON risk_scoring.rule_parameters(valid_from);
CREATE INDEX idx_rule_parameters_valid_to ON risk_scoring.rule_parameters(valid_to);
CREATE INDEX idx_rule_parameters_temporal ON risk_scoring.rule_parameters(rule_id, valid_from, valid_to);


-- ============================================================================
-- Table 5: rule_change_events (Immutable Audit Log)
-- ============================================================================
-- Immutable audit log of all rule parameter changes
CREATE TABLE risk_scoring.rule_change_events (
    event_id SERIAL PRIMARY KEY,
    parameter_id INTEGER REFERENCES risk_scoring.rule_parameters(parameter_id),
    rule_id INTEGER NOT NULL,
    change_type VARCHAR(50) NOT NULL,  -- 'INSERT', 'UPDATE', 'DELETE'
    old_value TEXT,
    new_value TEXT,
    changed_by VARCHAR(255),
    change_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT immutable_log CHECK (change_timestamp = DEFAULT)
);

CREATE INDEX idx_rule_change_events_rule_id ON risk_scoring.rule_change_events(rule_id);
CREATE INDEX idx_rule_change_events_timestamp ON risk_scoring.rule_change_events(change_timestamp);
CREATE INDEX idx_rule_change_events_parameter ON risk_scoring.rule_change_events(parameter_id);


-- ============================================================================
-- Table 6: model_scores
-- ============================================================================
-- Latest risk scores for entities
CREATE TABLE risk_scoring.model_scores (
    score_id SERIAL PRIMARY KEY,
    entity_id VARCHAR(255) NOT NULL,
    domain_id INTEGER NOT NULL REFERENCES risk_scoring.domains(domain_id),
    score NUMERIC(5, 4) NOT NULL CHECK (score BETWEEN 0 AND 1),
    confidence NUMERIC(5, 4) NOT NULL CHECK (confidence BETWEEN 0 AND 1),
    explanation JSONB,  -- {gate1: score, gate2: score, gate3: score, factors: {}}
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(entity_id, domain_id)
);

CREATE INDEX idx_model_scores_entity_domain ON risk_scoring.model_scores(entity_id, domain_id);
CREATE INDEX idx_model_scores_domain ON risk_scoring.model_scores(domain_id);
CREATE INDEX idx_model_scores_score ON risk_scoring.model_scores(score);
CREATE INDEX idx_model_scores_timestamp ON risk_scoring.model_scores(timestamp);


-- ============================================================================
-- Table 7: feedback
-- ============================================================================
-- Analyst feedback and ground truth labels for model improvement
CREATE TABLE risk_scoring.feedback (
    feedback_id SERIAL PRIMARY KEY,
    entity_id VARCHAR(255) NOT NULL,
    domain_id INTEGER NOT NULL REFERENCES risk_scoring.domains(domain_id),
    analyst_label VARCHAR(50) NOT NULL,  -- 'high_risk', 'medium_risk', 'low_risk', 'benign'
    confidence NUMERIC(5, 4) CHECK (confidence BETWEEN 0 AND 1),
    notes TEXT,
    analyst_id VARCHAR(255),
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_feedback_entity_domain ON risk_scoring.feedback(entity_id, domain_id);
CREATE INDEX idx_feedback_domain ON risk_scoring.feedback(domain_id);
CREATE INDEX idx_feedback_label ON risk_scoring.feedback(analyst_label);
CREATE INDEX idx_feedback_timestamp ON risk_scoring.feedback(timestamp);


-- ============================================================================
-- Table 8: model_training_runs
-- ============================================================================
-- Historical record of model training iterations
CREATE TABLE risk_scoring.model_training_runs (
    training_id SERIAL PRIMARY KEY,
    domain_id INTEGER NOT NULL REFERENCES risk_scoring.domains(domain_id),
    model_version_id INTEGER,
    training_start TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    training_end TIMESTAMP,
    training_size INTEGER NOT NULL,  -- number of samples
    auc NUMERIC(5, 4) CHECK (auc BETWEEN 0 AND 1),
    precision NUMERIC(5, 4) CHECK (precision BETWEEN 0 AND 1),
    recall NUMERIC(5, 4) CHECK (recall BETWEEN 0 AND 1),
    f1_score NUMERIC(5, 4) CHECK (f1_score BETWEEN 0 AND 1),
    hyperparameters JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_model_training_runs_domain ON risk_scoring.model_training_runs(domain_id);
CREATE INDEX idx_model_training_runs_training_start ON risk_scoring.model_training_runs(training_start);


-- ============================================================================
-- Table 9: drift_alerts
-- ============================================================================
-- Data drift detection and monitoring
CREATE TABLE risk_scoring.drift_alerts (
    alert_id SERIAL PRIMARY KEY,
    domain_id INTEGER NOT NULL REFERENCES risk_scoring.domains(domain_id),
    feature_name VARCHAR(255) NOT NULL,
    ks_statistic NUMERIC(5, 4) NOT NULL,  -- Kolmogorov-Smirnov statistic
    pvalue NUMERIC(10, 8) NOT NULL,
    drift_detected BOOLEAN DEFAULT FALSE,
    alert_level VARCHAR(50),  -- 'warning', 'critical'
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_drift_alerts_domain ON risk_scoring.drift_alerts(domain_id);
CREATE INDEX idx_drift_alerts_feature ON risk_scoring.drift_alerts(feature_name);
CREATE INDEX idx_drift_alerts_timestamp ON risk_scoring.drift_alerts(timestamp);
CREATE INDEX idx_drift_alerts_drift_detected ON risk_scoring.drift_alerts(drift_detected);


-- ============================================================================
-- Table 10: model_versions
-- ============================================================================
-- Model artifact versioning and deployment tracking
CREATE TABLE risk_scoring.model_versions (
    model_version_id SERIAL PRIMARY KEY,
    domain_id INTEGER NOT NULL REFERENCES risk_scoring.domains(domain_id),
    model_name VARCHAR(255) NOT NULL,
    model_type VARCHAR(50) NOT NULL,  -- 'xgboost', 'isolation_forest', 'shap_explainer'
    model_path VARCHAR(512) NOT NULL,  -- gs://cbp-sentry-models/cbp/xgboost/v1.pkl
    trained_at TIMESTAMP NOT NULL,
    deployed_at TIMESTAMP,
    retired_at TIMESTAMP,
    auc NUMERIC(5, 4) CHECK (auc BETWEEN 0 AND 1),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT model_deployment_temporal CHECK (deployed_at IS NULL OR deployed_at >= trained_at)
);

CREATE INDEX idx_model_versions_domain ON risk_scoring.model_versions(domain_id);
CREATE INDEX idx_model_versions_model_type ON risk_scoring.model_versions(model_type);
CREATE INDEX idx_model_versions_is_active ON risk_scoring.model_versions(is_active);
CREATE INDEX idx_model_versions_trained_at ON risk_scoring.model_versions(trained_at);


-- ============================================================================
-- Table 11: model_inference_cache
-- ============================================================================
-- Redis-synced cache for inference results (denormalized for performance)
CREATE TABLE risk_scoring.model_inference_cache (
    cache_id SERIAL PRIMARY KEY,
    entity_id VARCHAR(255) NOT NULL,
    domain_id INTEGER NOT NULL REFERENCES risk_scoring.domains(domain_id),
    score NUMERIC(5, 4) NOT NULL CHECK (score BETWEEN 0 AND 1),
    confidence NUMERIC(5, 4) NOT NULL CHECK (confidence BETWEEN 0 AND 1),
    cached_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,
    redis_key VARCHAR(512),
    UNIQUE(entity_id, domain_id)
);

CREATE INDEX idx_inference_cache_entity_domain ON risk_scoring.model_inference_cache(entity_id, domain_id);
CREATE INDEX idx_inference_cache_expires_at ON risk_scoring.model_inference_cache(expires_at);
CREATE INDEX idx_inference_cache_domain ON risk_scoring.model_inference_cache(domain_id);


-- ============================================================================
-- Table 12: model_performance_metrics
-- ============================================================================
-- Aggregated performance metrics for monitoring
CREATE TABLE risk_scoring.model_performance_metrics (
    metric_id SERIAL PRIMARY KEY,
    domain_id INTEGER NOT NULL REFERENCES risk_scoring.domains(domain_id),
    model_version_id INTEGER NOT NULL REFERENCES risk_scoring.model_versions(model_version_id),
    metric_name VARCHAR(255) NOT NULL,  -- 'accuracy', 'precision', 'recall', 'auc', 'f1'
    metric_value NUMERIC(5, 4) NOT NULL,
    measured_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    cohort_filter JSONB,  -- optional cohort (e.g., high_risk entities)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_model_performance_metrics_domain ON risk_scoring.model_performance_metrics(domain_id);
CREATE INDEX idx_model_performance_metrics_model_version ON risk_scoring.model_performance_metrics(model_version_id);
CREATE INDEX idx_model_performance_metrics_measured_at ON risk_scoring.model_performance_metrics(measured_at);


-- ============================================================================
-- Grants and Permissions
-- ============================================================================
-- Grant permissions to application role (adjust as needed)
-- GRANT USAGE ON SCHEMA risk_scoring TO app_role;
-- GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA risk_scoring TO app_role;
-- GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA risk_scoring TO app_role;

-- ============================================================================
-- Schema initialization complete
-- ============================================================================
