"""
Risk Scoring Model Validation Against Synthetic Dataset

Calculates precision, recall, F1, AUC-ROC metrics on 5K synthetic shipments
to validate model accuracy before production deployment.
"""

import json
import numpy as np
from typing import List, Tuple, Dict
from sklearn.metrics import (
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    confusion_matrix,
    classification_report,
    roc_curve,
)
from risk_scoring_engine import RiskScoringEngine


class ModelValidator:
    """Validate risk scoring model against ground truth"""

    def __init__(self, synthetic_dataset_path: str):
        self.engine = RiskScoringEngine()
        self.synthetic_data = self._load_dataset(synthetic_dataset_path)
        self.predictions = []
        self.ground_truth = []

    def _load_dataset(self, filepath: str) -> List[Dict]:
        """Load synthetic dataset"""
        with open(filepath, "r") as f:
            return json.load(f)

    def _outcome_to_label(self, outcome: str) -> int:
        """Convert outcome to binary label (1=HIGH_RISK, 0=LOW_RISK)"""
        # SEIZED and EXAMINED are "positive" (high-risk cases)
        # CLEARED is "negative" (low-risk cases)
        return 1 if outcome in ["SEIZED", "EXAMINED"] else 0

    def score_shipment_safe(self, shipment: Dict) -> float:
        """Score shipment with error handling"""
        try:
            breakdown = self.engine.score_shipment(shipment)
            return breakdown.final_score
        except Exception as e:
            # Default to neutral score if error
            print(f"⚠️  Error scoring {shipment.get('shipment_id')}: {e}")
            return 50.0

    def validate(self) -> Dict:
        """Validate model on entire dataset"""
        print("\n" + "=" * 70)
        print("MODEL VALIDATION ON SYNTHETIC DATASET")
        print("=" * 70)
        print(f"\nScoring {len(self.synthetic_data)} shipments...")

        # Score all shipments
        for idx, shipment in enumerate(self.synthetic_data):
            if (idx + 1) % 500 == 0:
                print(f"  Processed {idx + 1}/{len(self.synthetic_data)}")

            # Score shipment
            model_score = self.score_shipment_safe(shipment)
            self.predictions.append(model_score)

            # Get ground truth
            outcome = shipment.get("expected_outcome", "CLEARED")
            label = self._outcome_to_label(outcome)
            self.ground_truth.append(label)

        print(f"✓ Scored all shipments")

        # Convert to binary predictions (threshold: 70)
        threshold = 70
        binary_predictions = [1 if score >= threshold else 0 for score in self.predictions]

        # Calculate metrics
        precision = precision_score(self.ground_truth, binary_predictions, zero_division=0)
        recall = recall_score(self.ground_truth, binary_predictions, zero_division=0)
        f1 = f1_score(self.ground_truth, binary_predictions, zero_division=0)

        # AUC-ROC (probability of high-risk)
        # Normalize scores to 0-1 range for AUC
        normalized_scores = np.array(self.predictions) / 100.0
        auc = roc_auc_score(self.ground_truth, normalized_scores)

        # Confusion matrix
        tn, fp, fn, tp = confusion_matrix(self.ground_truth, binary_predictions).ravel()

        # Results
        results = {
            "threshold": threshold,
            "precision": precision,
            "recall": recall,
            "f1_score": f1,
            "auc_roc": auc,
            "confusion_matrix": {
                "true_negatives": int(tn),
                "false_positives": int(fp),
                "false_negatives": int(fn),
                "true_positives": int(tp),
            },
            "total_shipments": len(self.synthetic_data),
            "high_risk_predictions": sum(binary_predictions),
            "low_risk_predictions": len(binary_predictions) - sum(binary_predictions),
        }

        return results

    def print_results(self, results: Dict):
        """Print validation results"""
        print("\n" + "=" * 70)
        print("VALIDATION RESULTS")
        print("=" * 70)

        print(f"\nThreshold: {results['threshold']} (shipments >= this score flagged as HIGH_RISK)")
        print(f"\nMetrics:")
        print(f"  Precision: {results['precision']:.4f} (of flagged shipments, % actually risky)")
        print(f"  Recall:    {results['recall']:.4f} (of risky shipments, % we caught)")
        print(f"  F1 Score:  {results['f1_score']:.4f} (harmonic mean)")
        print(f"  AUC-ROC:   {results['auc_roc']:.4f} (probability of correct ranking)")

        cm = results["confusion_matrix"]
        print(f"\nConfusion Matrix:")
        print(f"  True Negatives:  {cm['true_negatives']:5d} (correctly cleared)")
        print(f"  False Positives: {cm['false_positives']:5d} (wrongly flagged)")
        print(f"  False Negatives: {cm['false_negatives']:5d} (wrongly cleared)")
        print(f"  True Positives:  {cm['true_positives']:5d} (correctly flagged)")

        print(f"\nPredictions:")
        print(
            f"  HIGH_RISK (≥{results['threshold']}): {results['high_risk_predictions']} ({results['high_risk_predictions']/results['total_shipments']*100:.1f}%)"
        )
        print(
            f"  LOW_RISK (<{results['threshold']}): {results['low_risk_predictions']} ({results['low_risk_predictions']/results['total_shipments']*100:.1f}%)"
        )

        print(f"\nGoals (Phase 2 Success Criteria):")
        print(f"  Precision ≥ 0.70: {'✓ PASS' if results['precision'] >= 0.70 else '✗ FAIL'}")
        print(f"  Recall ≥ 0.65:    {'✓ PASS' if results['recall'] >= 0.65 else '✗ FAIL'}")
        print(f"  F1 Score ≥ 0.67:  {'✓ PASS' if results['f1_score'] >= 0.67 else '✗ FAIL'}")
        print(f"  AUC-ROC ≥ 0.75:   {'✓ PASS' if results['auc_roc'] >= 0.75 else '✗ FAIL'}")

        print("\n" + "=" * 70)

    def save_results(self, results: Dict, filepath: str):
        """Save results to JSON"""
        with open(filepath, "w") as f:
            json.dump(results, f, indent=2)
        print(f"\n✓ Results saved to {filepath}")


if __name__ == "__main__":
    validator = ModelValidator("/home/rahulvadera/cbp-sentry/services/api/synthetic_dataset_5000.json")
    results = validator.validate()
    validator.print_results(results)
    validator.save_results(results, "/home/rahulvadera/cbp-sentry/services/api/model_validation_results.json")
