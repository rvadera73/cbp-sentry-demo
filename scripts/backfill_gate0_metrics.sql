-- Backfill real, measured performance metrics + training history for the
-- production model (gate0-v1.0, model_version_id = 4) into the risk_scoring
-- schema the cbp-risk-engine reads from PostgreSQL.
--
-- Values are the genuine XGBoost training results from
-- test-results/clean_training_results.json (job train-20260624172548).
-- We intentionally do NOT seed latency_p95 / consistency / fairness /
-- error_rate / compliance: those are not yet measured at 15% maturity, so the
-- gate evaluator should honestly report them as "no measured value".
--
-- Idempotent: safe to re-run.

BEGIN;

-- 1) Performance metrics (real, measured) for gate0-v1.0
DELETE FROM risk_scoring.model_performance_metrics
WHERE model_version_id = 4
  AND metric_name IN ('auc','accuracy','precision','recall','f1_score',
                      'training_samples','test_samples','feature_count');

INSERT INTO risk_scoring.model_performance_metrics
    (model_version_id, metric_name, metric_value, timestamp, created_at)
VALUES
    (4, 'auc',              0.9934324217508893, TIMESTAMP '2026-06-24 17:26:59', NOW()),
    (4, 'accuracy',         0.974409,           TIMESTAMP '2026-06-24 17:26:59', NOW()),
    (4, 'precision',        0.5290322580645161, TIMESTAMP '2026-06-24 17:26:59', NOW()),
    (4, 'recall',           0.9534883720930233, TIMESTAMP '2026-06-24 17:26:59', NOW()),
    (4, 'f1_score',         0.6804979253112033, TIMESTAMP '2026-06-24 17:26:59', NOW()),
    (4, 'training_samples', 7200,               TIMESTAMP '2026-06-24 17:26:59', NOW()),
    (4, 'test_samples',     3087,               TIMESTAMP '2026-06-24 17:26:59', NOW()),
    (4, 'feature_count',    36,                 TIMESTAMP '2026-06-24 17:26:59', NOW());

-- 2) Training run history (real job) for gate0-v1.0
DELETE FROM risk_scoring.model_training_runs
WHERE job_id = 'train-20260624172548-5efd39c7';

INSERT INTO risk_scoring.model_training_runs
    (model_version_id, job_id, status, started_at, completed_at,
     training_records, test_records, hyperparameters, training_metrics, created_at)
VALUES (
    4,
    'train-20260624172548-5efd39c7',
    'completed',
    TIMESTAMP '2026-06-24 17:25:48',
    TIMESTAMP '2026-06-24 17:26:59',
    7200,
    3087,
    '{"model_type": "xgboost", "notes": "Gate 0 baseline training (clean 36-feature set)"}'::jsonb,
    '{"auc": 0.9934324217508893, "precision": 0.5290322580645161, "recall": 0.9534883720930233, "f1": 0.6804979253112033, "feature_count": 36, "training_samples": 7200, "test_samples": 3087}'::jsonb,
    NOW()
);

COMMIT;

\echo '--- performance metrics for gate0 (version 4) ---'
SELECT metric_name, metric_value FROM risk_scoring.model_performance_metrics
WHERE model_version_id = 4 ORDER BY metric_name;
\echo '--- training runs ---'
SELECT job_id, status, training_records, test_records FROM risk_scoring.model_training_runs;
