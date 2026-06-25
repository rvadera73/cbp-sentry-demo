-- ============================================================================
-- CBP Sentry: CBP Domain Initialization (Phase 1)
-- ============================================================================
-- Registers the CBP domain and initializes the 7-factor risk scoring engine
-- with 3 gates, 8 rules, and pre-configured thresholds.
-- ============================================================================

-- ============================================================================
-- CBP Domain Registration
-- ============================================================================
INSERT INTO risk_scoring.domains (name, description, created_at)
VALUES (
    'cbp_illegal_transshipment',
    'Customs and Border Protection - Illegal Transshipment Detection Engine. 7-factor risk model with 3 gates (destination, entity, shipment) and 8 rules.',
    CURRENT_TIMESTAMP
) ON CONFLICT (name) DO NOTHING;

-- Get domain_id for reference
-- (Use CTE approach or subsequent SELECT if needed in client)
-- SELECT domain_id INTO cbp_domain_id FROM risk_scoring.domains WHERE name = 'cbp_illegal_transshipment';


-- ============================================================================
-- Feature Catalog: CBP Domain
-- ============================================================================
-- These 7 factors represent the core risk indicators:
-- 1. shipper_sanction_risk
-- 2. destination_risk
-- 3. entity_history
-- 4. shipment_pattern_anomaly
-- 5. product_risk
-- 6. routing_anomaly
-- 7. regulatory_flag_history

INSERT INTO risk_scoring.features_cbp (name, description, type, data_type, created_at)
VALUES
    ('shipper_sanction_risk',
     'Shipper entity matched to OFAC, SDN, or other sanction list with confidence score',
     'categorical', 'float', CURRENT_TIMESTAMP),

    ('destination_risk',
     'Destination country/port risk score based on TCA, sanctions, and transshipment history',
     'categorical', 'float', CURRENT_TIMESTAMP),

    ('entity_history',
     'Entity compliance history: prior violations, case counts, and analyst flagging',
     'categorical', 'integer', CURRENT_TIMESTAMP),

    ('shipment_pattern_anomaly',
     'Statistical anomaly in shipment frequency, quantity, or value vs. baseline',
     'numerical', 'float', CURRENT_TIMESTAMP),

    ('product_risk',
     'Product category risk: HTS code, controlled items, dual-use classification',
     'categorical', 'float', CURRENT_TIMESTAMP),

    ('routing_anomaly',
     'Unusual routing pattern: consolidation, re-export, or multi-hop detected',
     'categorical', 'float', CURRENT_TIMESTAMP),

    ('regulatory_flag_history',
     'Count of regulatory flags, holds, and enforcement actions',
     'numerical', 'integer', CURRENT_TIMESTAMP)
ON CONFLICT (name) DO NOTHING;


-- ============================================================================
-- Scorecard Configuration: CBP 7-Factor Engine
-- ============================================================================
-- 3 Gates (sequential decision boundaries):
-- - Gate 1 (Destination Risk): 0.70 threshold
-- - Gate 2 (Entity Assessment): 0.65 threshold
-- - Gate 3 (Shipment Anomaly): 0.60 threshold
--
-- 8 Rules:
-- R1: OFAC Sanction Match (Gate 1)
-- R2: High-Risk Destination (Gate 1)
-- R3: Entity Repeat Violator (Gate 2)
-- R4: Conflicting Entity Data (Gate 2)
-- R5: Anomalous Quantity Jump (Gate 3)
-- R6: Unusual Routing Pattern (Gate 3)
-- R7: Controlled Product + High-Risk Destination (Gate 3)
-- R8: Regulatory Hold History (Gate 2)

INSERT INTO risk_scoring.scorecards (
    domain_id,
    factors,
    rules,
    thresholds,
    created_at
)
SELECT
    (SELECT domain_id FROM risk_scoring.domains WHERE name = 'cbp_illegal_transshipment'),
    -- 7 Factors with equal weights (0.143 each for normalization)
    jsonb_build_object(
        'shipper_sanction_risk', 0.143,
        'destination_risk', 0.143,
        'entity_history', 0.143,
        'shipment_pattern_anomaly', 0.143,
        'product_risk', 0.143,
        'routing_anomaly', 0.143,
        'regulatory_flag_history', 0.143
    ),
    -- 3 Gates with 8 Rules total
    jsonb_build_object(
        'gate_1_destination_risk', jsonb_build_array(1, 2),
        'gate_2_entity_assessment', jsonb_build_array(3, 4, 8),
        'gate_3_shipment_anomaly', jsonb_build_array(5, 6, 7)
    ),
    -- Gate Thresholds (cumulative risk score)
    jsonb_build_object(
        'gate_1', 0.70,
        'gate_2', 0.65,
        'gate_3', 0.60
    ),
    CURRENT_TIMESTAMP
WHERE NOT EXISTS (
    SELECT 1 FROM risk_scoring.scorecards
    WHERE domain_id = (SELECT domain_id FROM risk_scoring.domains WHERE name = 'cbp_illegal_transshipment')
);


-- ============================================================================
-- Rule Parameter Initialization
-- ============================================================================
-- Define parameters for each rule with SCD Type 2 versioning

-- Rule 1: OFAC Sanction Match
INSERT INTO risk_scoring.rule_parameters (
    rule_id, parameter_name, parameter_value, valid_from, valid_to, created_at
)
VALUES
    (1, 'sanction_source', 'OFAC_SDN', CURRENT_TIMESTAMP, NULL, CURRENT_TIMESTAMP),
    (1, 'confidence_threshold', '0.85', CURRENT_TIMESTAMP, NULL, CURRENT_TIMESTAMP),
    (1, 'match_type', 'exact_or_fuzzy', CURRENT_TIMESTAMP, NULL, CURRENT_TIMESTAMP)
ON CONFLICT DO NOTHING;

-- Rule 2: High-Risk Destination
INSERT INTO risk_scoring.rule_parameters (
    rule_id, parameter_name, parameter_value, valid_from, valid_to, created_at
)
VALUES
    (2, 'risk_sources', 'OFAC_Countries,TCA_Ports,Transshipment_History', CURRENT_TIMESTAMP, NULL, CURRENT_TIMESTAMP),
    (2, 'risk_threshold', '0.70', CURRENT_TIMESTAMP, NULL, CURRENT_TIMESTAMP),
    (2, 'lookback_days', '730', CURRENT_TIMESTAMP, NULL, CURRENT_TIMESTAMP)
ON CONFLICT DO NOTHING;

-- Rule 3: Entity Repeat Violator
INSERT INTO risk_scoring.rule_parameters (
    rule_id, parameter_name, parameter_value, valid_from, valid_to, created_at
)
VALUES
    (3, 'violation_count_threshold', '3', CURRENT_TIMESTAMP, NULL, CURRENT_TIMESTAMP),
    (3, 'lookback_days', '1095', CURRENT_TIMESTAMP, NULL, CURRENT_TIMESTAMP),
    (3, 'case_severity_weight', 'severe:1.0,moderate:0.5,minor:0.2', CURRENT_TIMESTAMP, NULL, CURRENT_TIMESTAMP)
ON CONFLICT DO NOTHING;

-- Rule 4: Conflicting Entity Data
INSERT INTO risk_scoring.rule_parameters (
    rule_id, parameter_name, parameter_value, valid_from, valid_to, created_at
)
VALUES
    (4, 'conflict_types', 'address_mismatch,name_variance,identity_switching', CURRENT_TIMESTAMP, NULL, CURRENT_TIMESTAMP),
    (4, 'variance_threshold', '0.80', CURRENT_TIMESTAMP, NULL, CURRENT_TIMESTAMP)
ON CONFLICT DO NOTHING;

-- Rule 5: Anomalous Quantity Jump
INSERT INTO risk_scoring.rule_parameters (
    rule_id, parameter_name, parameter_value, valid_from, valid_to, created_at
)
VALUES
    (5, 'baseline_window_days', '180', CURRENT_TIMESTAMP, NULL, CURRENT_TIMESTAMP),
    (5, 'deviation_threshold', '2.5', CURRENT_TIMESTAMP, NULL, CURRENT_TIMESTAMP),
    (5, 'min_baseline_samples', '5', CURRENT_TIMESTAMP, NULL, CURRENT_TIMESTAMP)
ON CONFLICT DO NOTHING;

-- Rule 6: Unusual Routing Pattern
INSERT INTO risk_scoring.rule_parameters (
    rule_id, parameter_name, parameter_value, valid_from, valid_to, created_at
)
VALUES
    (6, 'routing_anomaly_types', 'multi_hop,consolidation,re_export', CURRENT_TIMESTAMP, NULL, CURRENT_TIMESTAMP),
    (6, 'anomaly_score_threshold', '0.65', CURRENT_TIMESTAMP, NULL, CURRENT_TIMESTAMP)
ON CONFLICT DO NOTHING;

-- Rule 7: Controlled Product + High-Risk Destination
INSERT INTO risk_scoring.rule_parameters (
    rule_id, parameter_name, parameter_value, valid_from, valid_to, created_at
)
VALUES
    (7, 'controlled_product_lists', 'BIS_EAR,AECA,ITAR', CURRENT_TIMESTAMP, NULL, CURRENT_TIMESTAMP),
    (7, 'destination_risk_threshold', '0.70', CURRENT_TIMESTAMP, NULL, CURRENT_TIMESTAMP)
ON CONFLICT DO NOTHING;

-- Rule 8: Regulatory Hold History
INSERT INTO risk_scoring.rule_parameters (
    rule_id, parameter_name, parameter_value, valid_from, valid_to, created_at
)
VALUES
    (8, 'hold_count_threshold', '2', CURRENT_TIMESTAMP, NULL, CURRENT_TIMESTAMP),
    (8, 'lookback_days', '365', CURRENT_TIMESTAMP, NULL, CURRENT_TIMESTAMP)
ON CONFLICT DO NOTHING;


-- ============================================================================
-- Audit Log Entry for Initial Configuration
-- ============================================================================
-- Record this initialization event in the immutable audit log

INSERT INTO risk_scoring.rule_change_events (
    rule_id, change_type, old_value, new_value, changed_by, change_timestamp, created_at
)
VALUES
    (1, 'INSERT', NULL, 'OFAC_sanction_match_initialized', 'system_init', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    (2, 'INSERT', NULL, 'High_risk_destination_initialized', 'system_init', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    (3, 'INSERT', NULL, 'Entity_repeat_violator_initialized', 'system_init', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    (4, 'INSERT', NULL, 'Conflicting_entity_data_initialized', 'system_init', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    (5, 'INSERT', NULL, 'Anomalous_quantity_jump_initialized', 'system_init', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    (6, 'INSERT', NULL, 'Unusual_routing_pattern_initialized', 'system_init', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    (7, 'INSERT', NULL, 'Controlled_product_high_risk_dest_initialized', 'system_init', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    (8, 'INSERT', NULL, 'Regulatory_hold_history_initialized', 'system_init', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
ON CONFLICT DO NOTHING;


-- ============================================================================
-- Verification Query (for testing)
-- ============================================================================
-- SELECT
--     d.domain_id, d.name, d.description,
--     sc.factors, sc.rules, sc.thresholds
-- FROM risk_scoring.domains d
-- LEFT JOIN risk_scoring.scorecards sc ON d.domain_id = sc.domain_id
-- WHERE d.name = 'cbp_illegal_transshipment';

-- SELECT
--     f.name, f.description, f.type, f.data_type
-- FROM risk_scoring.features_cbp f
-- ORDER BY f.feature_id;

-- SELECT
--     rule_id, parameter_name, parameter_value, valid_from, valid_to
-- FROM risk_scoring.rule_parameters
-- ORDER BY rule_id, parameter_name;

-- ============================================================================
-- CBP Domain Initialization Complete
-- ============================================================================
