"""Mock Data Service for Risk Model Management Development

Generates realistic mock data for development and testing.
Provides functions to populate all 8 UI screens with sample data.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Any
import random
import json


class RiskModelMockService:
    """Generates realistic mock data for Risk Model Management tab"""

    def __init__(self):
        self.origins = ['CN', 'MX', 'IN', 'HK', 'VN', 'TH', 'SG']
        self.commodities = ['ELEC', 'TEXT', 'MACH', 'FOOD', 'AUTO', 'PHARM']
        self.corridors = ['CN-LAX', 'MX-HOU', 'CN-NY', 'IN-NJ']

    # ========================================================================
    # DASHBOARD DATA
    # ========================================================================

    def get_mock_dashboard(self) -> Dict[str, Any]:
        """Get complete dashboard summary"""
        return {
            'active_model': {
                'model_id': 'v3.0',
                'version': 'v3.0',
                'status': 'production',
                'deployed_at': datetime.utcnow().isoformat(),
                'approved_by': 'Sarah Chen',
                'metrics': {
                    'accuracy': round(0.924 + random.uniform(-0.005, 0.005), 3),
                    'auc_roc': round(0.944 + random.uniform(-0.005, 0.005), 3),
                    'latency_p95_ms': int(85 + random.uniform(-5, 5)),
                    'confidence_avg': round(0.87 + random.uniform(-0.02, 0.02), 2),
                    'predictions_24h': 15432
                }
            },
            'pending_approvals': self.get_mock_pending_approvals(),
            'alerts': self.get_mock_alerts(),
            'key_metrics': {
                'accuracy': 0.924,
                'latency_p95': 85,
                'confidence_avg': 0.87,
                'data_drift_score': 0.12,
                'model_drift_score': 0.08
            }
        }

    # ========================================================================
    # MODEL VERSIONS DATA
    # ========================================================================

    def get_mock_versions(self) -> List[Dict[str, Any]]:
        """Get all model versions with metrics"""
        return [
            {
                'model_id': 'v3.0',
                'version': 'v3.0',
                'status': 'production',
                'framework': 'xgboost',
                'feature_count': 47,
                'weights_sum': 100.0,
                'deployed_at': (datetime.utcnow() - timedelta(hours=12)).isoformat(),
                'created_by': 'ML Team',
                'approved_by': 'Sarah Chen',
                'approval_date': (datetime.utcnow() - timedelta(hours=12)).isoformat(),
                'performance_metrics': {
                    'accuracy': 0.924,
                    'auc_roc': 0.944,
                    'latency_p95_ms': 85,
                    'false_positive_rate': 0.032
                }
            },
            {
                'model_id': 'v3.1',
                'version': 'v3.1',
                'status': 'candidate',
                'framework': 'xgboost',
                'feature_count': 47,
                'weights_sum': 100.0,
                'created_by': 'ML Team',
                'approval_status': 'under_review',
                'approval_votes': 1,  # out of 2
                'performance_metrics': {
                    'accuracy': 0.931,
                    'auc_roc': 0.951,
                    'latency_p95_ms': 87,
                    'false_positive_rate': 0.028
                },
                'delta_vs_v3_0': {
                    'accuracy': 0.007,
                    'auc_roc': 0.007,
                    'latency': 2
                }
            },
            {
                'model_id': 'v2.1',
                'version': 'v2.1',
                'status': 'deprecated',
                'framework': 'xgboost',
                'feature_count': 47,
                'weights_sum': 110.0,  # Invalid!
                'deprecated_at': (datetime.utcnow() - timedelta(hours=12)).isoformat(),
                'note': 'Replaced by v3.0',
                'performance_metrics': {
                    'accuracy': 0.914,
                    'auc_roc': 0.938,
                    'latency_p95_ms': 82,
                    'false_positive_rate': 0.035
                }
            }
        ]

    # ========================================================================
    # TRAINING HISTORY DATA
    # ========================================================================

    def get_mock_training_jobs(self) -> List[Dict[str, Any]]:
        """Get training job history"""
        now = datetime.utcnow()
        return [
            {
                'job_id': 'job-20260611-093001',
                'model_id': 'v3.1',
                'status': 'completed',
                'started_at': (now - timedelta(days=2)).isoformat(),
                'completed_at': (now - timedelta(days=2, hours=2, minutes=15)).isoformat(),
                'duration_minutes': 135,
                'dataset': {
                    'id': 'cbp-shipments-2024',
                    'records': 2500000,
                    'features': 47,
                    'train_test_split': '80/20'
                },
                'hyperparameters': {
                    'max_depth': 8,
                    'learning_rate': 0.05,
                    'n_estimators': 500
                },
                'training_metrics': {
                    'training_accuracy': 0.938,
                    'test_accuracy': 0.931,
                    'auc_roc': 0.951
                },
                'validation_status': 'passed',
                'approval_status': 'under_review',
                'approval_votes': 1,
                'top_features': [
                    {'name': 'documentation_risk', 'importance': 0.253},
                    {'name': 'corridor_risk', 'importance': 0.198},
                    {'name': 'routing_risk', 'importance': 0.149}
                ]
            },
            {
                'job_id': 'job-20260612-143501',
                'model_id': 'v3.0',
                'status': 'completed',
                'started_at': (now - timedelta(days=1)).isoformat(),
                'completed_at': (now - timedelta(days=1, hours=2, minutes=5)).isoformat(),
                'duration_minutes': 125,
                'dataset': {
                    'id': 'cbp-shipments-2024',
                    'records': 2500000,
                    'features': 47,
                    'train_test_split': '80/20'
                },
                'validation_status': 'passed',
                'training_metrics': {
                    'training_accuracy': 0.932,
                    'test_accuracy': 0.924,
                    'auc_roc': 0.944
                },
                'approval_status': 'approved',
                'approved_at': (now - timedelta(hours=10)).isoformat(),
                'deployed_at': (now - timedelta(hours=12)).isoformat(),
                'top_features': [
                    {'name': 'documentation_risk', 'importance': 0.250},
                    {'name': 'corridor_risk', 'importance': 0.200},
                    {'name': 'routing_risk', 'importance': 0.150}
                ]
            },
            {
                'job_id': 'job-20260613-020000',
                'model_id': 'v3.2',
                'status': 'running',
                'started_at': (now - timedelta(hours=1, minutes=30)).isoformat(),
                'progress_percent': 45,
                'current_step': 'model_training',
                'steps': [
                    {'name': 'data_prep', 'status': 'completed'},
                    {'name': 'feature_engineering', 'status': 'completed'},
                    {'name': 'model_training', 'status': 'running'},
                    {'name': 'validation', 'status': 'queued'},
                    {'name': 'artifact_storage', 'status': 'queued'},
                    {'name': 'notification', 'status': 'queued'}
                ],
                'eta_minutes': 75,
                'estimated_completion': (now + timedelta(minutes=75)).isoformat()
            },
            {
                'job_id': 'job-20260610-140000',
                'model_id': 'v2.2',
                'status': 'failed',
                'started_at': (now - timedelta(days=3)).isoformat(),
                'failed_at': (now - timedelta(days=3, minutes=30)).isoformat(),
                'error': 'ValidationError',
                'reason': 'Test accuracy < 0.90 threshold',
                'validation_status': 'failed'
            }
        ]

    # ========================================================================
    # PERFORMANCE METRICS DATA
    # ========================================================================

    def get_mock_metrics_timeseries(self, hours: int = 24, metric: str = 'accuracy') -> List[Dict[str, Any]]:
        """Generate time-series performance metrics"""
        metrics = []
        base_value = 0.92 if metric == 'accuracy' else 85 if metric == 'latency' else 0.87

        for i in range(hours):
            ts = datetime.utcnow() - timedelta(hours=hours - i)
            noise = random.uniform(-0.002, 0.002) if metric == 'accuracy' else random.uniform(-2, 2)

            metrics.append({
                'timestamp': ts.isoformat(),
                'metric': metric,
                'value': round(base_value + noise, 3) if metric == 'accuracy' else int(base_value + noise),
                'segment': None
            })

        return metrics

    def get_mock_fairness_metrics(self, segment_by: str = 'origin') -> List[Dict[str, Any]]:
        """Get fairness metrics by segment"""
        segments = {
            'origin': ['CN', 'MX', 'IN', 'HK', 'VN', 'Other'],
            'commodity': ['ELEC', 'TEXT', 'MACH', 'FOOD', 'AUTO', 'PHARM'],
            'corridor': ['CN-LAX', 'MX-HOU', 'CN-NY', 'IN-NJ', 'Other']
        }

        results = []
        base_accuracy = 0.924

        for segment in segments.get(segment_by, ['Other']):
            variance = random.uniform(-0.01, 0.01)
            results.append({
                'segment': f'{segment_by}={segment}',
                'accuracy': round(base_accuracy + variance, 3),
                'precision': round(0.92 + variance, 3),
                'recall': round(0.93 + variance, 3),
                'fairness_score': round(0.92 + variance, 2)
            })

        return results

    # ========================================================================
    # DATA DRIFT DATA
    # ========================================================================

    def get_mock_drift_detection(self) -> Dict[str, Any]:
        """Get current drift status"""
        return {
            'overall_drift_score': 0.12,
            'status': 'normal',
            'elevated_features': [
                {
                    'feature': 'origin_country',
                    'drift_score': 0.34,
                    'status': 'elevated',
                    'detected_at': (datetime.utcnow() - timedelta(hours=2)).isoformat(),
                    'baseline_distribution': {
                        'CN': 0.324,
                        'MX': 0.221,
                        'IN': 0.205,
                        'HK': 0.082,
                        'Other': 0.168
                    },
                    'current_distribution': {
                        'CN': 0.289,
                        'MX': 0.243,
                        'IN': 0.228,
                        'HK': 0.091,
                        'Other': 0.149
                    },
                    'recommendation': 'Monitor for 48h before retraining'
                }
            ],
            'normal_features': [
                {
                    'feature': 'commodity_value',
                    'drift_score': 0.08,
                    'status': 'normal',
                    'baseline_mean': 2145,
                    'baseline_std': 1240,
                    'current_mean': 2168,
                    'current_std': 1255
                }
            ]
        }

    # ========================================================================
    # PREDICTION EXPLANATION DATA (SHAP)
    # ========================================================================

    def get_mock_shap_explanation(self, shipment_id: str) -> Dict[str, Any]:
        """Get SHAP explanation for a prediction"""
        return {
            'shipment': {
                'id': shipment_id,
                'origin': random.choice(self.origins),
                'destination': 'US Port',
                'commodity': random.choice(self.commodities),
                'declared_value': int(random.uniform(10000, 500000)),
                'container_type': random.choice(['20ft FCL', '40ft FCL', 'LCL'])
            },
            'prediction': {
                'model_version': 'v3.0',
                'score': round(random.uniform(0.3, 0.9), 2),
                'confidence': round(random.uniform(0.75, 0.95), 2),
                'classification': random.choice(['CLEAR', 'EXAMINE', 'HOLD']),
                'processing_time_ms': int(random.uniform(70, 120))
            },
            'shap_explanation': {
                'base_score': 0.35,
                'factors_increasing_risk': [
                    {
                        'feature': 'documentation_risk',
                        'value': 0.85,
                        'contribution': 0.16,
                        'rank': 1
                    },
                    {
                        'feature': 'routing_risk',
                        'value': 'HIGH',
                        'contribution': 0.14,
                        'rank': 2
                    },
                    {
                        'feature': 'pattern_risk',
                        'value': 'UNUSUAL',
                        'contribution': 0.07,
                        'rank': 3
                    }
                ],
                'factors_decreasing_risk': [
                    {
                        'feature': 'party_risk',
                        'value': 'LOW',
                        'contribution': -0.04,
                        'rank': 1
                    }
                ]
            },
            'interpretation': 'Flagged for examination due to documentation issues and routing concerns.'
        }

    # ========================================================================
    # APPROVAL DATA
    # ========================================================================

    def get_mock_pending_approvals(self) -> List[Dict[str, Any]]:
        """Get pending approval requests"""
        now = datetime.utcnow()
        return [
            {
                'approval_request_id': 'apr-20260611',
                'model_id': 'v3.1',
                'requested_by': 'Alex Kim',
                'requested_at': (now - timedelta(days=1)).isoformat(),
                'request_reason': '+0.7% accuracy, lower FPR',
                'status': 'pending',
                'performance_improvement': {
                    'accuracy': {'before': 0.924, 'after': 0.931, 'delta': 0.007},
                    'auc_roc': {'before': 0.944, 'after': 0.951, 'delta': 0.007},
                    'latency': {'before': 85, 'after': 87, 'delta': 2}
                },
                'voters': [
                    {
                        'voter': 'Sarah Chen',
                        'role': 'Manager',
                        'vote': 'approve',
                        'comment': 'Solid improvement. FPR reduction is significant',
                        'voted_at': (now - timedelta(hours=10)).isoformat()
                    },
                    {
                        'voter': 'John Davis',
                        'role': 'Tech Lead',
                        'vote': None,
                        'status': 'pending',
                        'email_sent_at': (now - timedelta(hours=23)).isoformat()
                    }
                ],
                'approval_threshold': '2/2',
                'deadline': (now + timedelta(days=1)).isoformat()
            }
        ]

    # ========================================================================
    # RETRAINING CONFIG DATA
    # ========================================================================

    def get_mock_retraining_config(self) -> Dict[str, Any]:
        """Get retraining configuration"""
        now = datetime.utcnow()
        return {
            'scheduled': {
                'enabled': True,
                'frequency': 'weekly',
                'day': 'monday',
                'time': '02:00',
                'timezone': 'UTC',
                'data_window_days': 7,
                'next_run': (now + timedelta(days=3)).isoformat(),
                'last_run': (now - timedelta(days=4)).isoformat(),
                'last_run_status': 'passed'
            },
            'drift_triggered': {
                'enabled': True,
                'drift_threshold': 0.30,
                'persistence_hours': 24,
                'affected_features_min': 3,
                'last_triggered': (now - timedelta(days=7)).isoformat(),
                'last_triggered_feature': 'origin_country'
            },
            'model_drift_triggered': {
                'enabled': True,
                'degradation_threshold': -0.02,
                'evaluation_window_days': 7,
                'min_predictions': 10000,
                'last_triggered': (now - timedelta(days=11)).isoformat()
            },
            'error_triggered': {
                'enabled': False,
                'error_threshold': 0.05,
                'persistence_minutes': 30
            }
        }

    # ========================================================================
    # ALERTS DATA
    # ========================================================================

    def get_mock_alerts(self) -> List[Dict[str, Any]]:
        """Get current alerts"""
        return [
            {
                'type': 'data_drift',
                'feature': 'origin_country',
                'drift_score': 0.34,
                'detected_at': (datetime.utcnow() - timedelta(hours=2)).isoformat(),
                'severity': 'warning',
                'recommendation': 'Monitor for 48h before retraining'
            }
        ]


# Singleton instance
_mock_service = None


def get_mock_service() -> RiskModelMockService:
    """Get mock service singleton"""
    global _mock_service
    if _mock_service is None:
        _mock_service = RiskModelMockService()
    return _mock_service
