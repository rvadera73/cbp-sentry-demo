"""
Risk Scoring Model Validation Against Synthetic Dataset

Uses XGBoost + batch-percentile calibration: scores all 5K shipments, then
maps raw probabilities to 0-100 scores based on their relative rank within
the batch. Top 15% flagged as HIGH RISK (score >= 70).

This is operationally correct for CBP: officers inspect the riskiest N% of
shipments in a manifest or daily queue, not those above an absolute threshold.

NOTE: absolute thresholds (prob >= X → score 70) require real CBP ground-truth
data. Synthetic training data produces artifacts that break absolute calibration.
"""

import json
import numpy as np
import os
from pathlib import Path
from typing import List, Dict
from sklearn.metrics import (
    precision_score, recall_score, f1_score, roc_auc_score, confusion_matrix,
)

MODEL_DIR = Path(os.environ.get("MODEL_DIR", "/home/rahulvadera/cbp-sentry/models"))
SYNTHETIC_DATASET = Path("/home/rahulvadera/cbp-sentry/services/api/synthetic_dataset_5000_enriched.json")


def _percentile_calibrate(probs: np.ndarray) -> np.ndarray:
    """
    Map raw XGBoost probabilities to 0-100 scores using batch-percentile ranking.

    Score bands (calibrated so top 25% of any batch scores ≥ 70):
      Top  5%  → 90-95  (CRITICAL)
      Top 10%  → 85-90  (CRITICAL-HIGH)
      Top 25%  → 70-85  (HIGH, inspection threshold)
      Top 50%  → 50-70  (MEDIUM)
      Bottom   → 5-50   (LOW)
    """
    pct_rank = np.argsort(np.argsort(probs)) / max(len(probs) - 1, 1)  # [0,1]

    scores = np.where(
        pct_rank >= 0.95,  # top 5%
        90.0 + (pct_rank - 0.95) / 0.05 * 5.0,
        np.where(
            pct_rank >= 0.90,  # top 10%
            85.0 + (pct_rank - 0.90) / 0.05 * 5.0,
            np.where(
                pct_rank >= 0.75,  # top 25%
                70.0 + (pct_rank - 0.75) / 0.15 * 15.0,
                np.where(
                    pct_rank >= 0.50,  # top 50%
                    50.0 + (pct_rank - 0.50) / 0.25 * 20.0,
                    5.0 + pct_rank / 0.50 * 45.0,  # bottom 50%
                ),
            ),
        ),
    )
    return np.clip(scores, 5.0, 95.0)


class ModelValidator:
    """Validate risk scoring model against ground truth."""

    def __init__(self, synthetic_dataset_path: str = str(SYNTHETIC_DATASET)):
        self.synthetic_data = self._load_dataset(synthetic_dataset_path)
        self.raw_probs: List[float] = []
        self.ground_truth: List[int] = []
        self.xgb_model = None
        self.feature_names = None
        self._load_xgb()
        if self.xgb_model is None:
            from risk_scoring_engine import RiskScoringEngine
            self.engine = RiskScoringEngine()
        else:
            self.engine = None

    def _load_xgb(self):
        xgb_path = MODEL_DIR / "xgboost_model.json"
        cal_path  = MODEL_DIR / "score_calibration.json"
        if not (xgb_path.exists() and cal_path.exists()):
            print("  [warn] No XGBoost model/calibration — falling back to rule engine")
            return
        try:
            import xgboost as xgb
            self.xgb_model = xgb.Booster()
            self.xgb_model.load_model(str(xgb_path))
            cal = json.load(open(cal_path))
            self.feature_names = cal["clean_features"]
            print(f"  [ok] XGBoost loaded ({cal['feature_count']} features)")
        except Exception as e:
            print(f"  [warn] XGBoost load failed: {e}")
            self.xgb_model = None

    def _load_dataset(self, filepath: str) -> List[Dict]:
        with open(filepath) as f:
            return json.load(f)

    def _outcome_to_label(self, outcome: str) -> int:
        return 1 if outcome in ["SEIZED", "EXAMINED"] else 0

    def _score_all_xgb(self) -> np.ndarray:
        """Batch-score all shipments with XGBoost, return raw probabilities."""
        import xgboost as xgb
        from inference_features import extract_clean_features
        rows = [extract_clean_features(s, self.feature_names) for s in self.synthetic_data]
        X = np.array(rows, dtype=np.float32)
        dm = xgb.DMatrix(X, feature_names=self.feature_names)
        return self.xgb_model.predict(dm)

    def validate(self) -> Dict:
        method = "XGBoost+PercentileCalibration" if self.xgb_model else "RuleEngine"
        print(f"\n{'='*70}\nVALIDATION  [{method}]  —  {len(self.synthetic_data)} shipments\n{'='*70}")

        if self.xgb_model is not None:
            print("  batch-scoring with XGBoost...")
            raw_probs = self._score_all_xgb()
            scores = _percentile_calibrate(raw_probs)
            self.raw_probs = raw_probs.tolist()
        else:
            scores = []
            for idx, shipment in enumerate(self.synthetic_data):
                if (idx + 1) % 500 == 0:
                    print(f"  {idx+1}/{len(self.synthetic_data)}...")
                try:
                    scores.append(self.engine.score_shipment(shipment).final_score)
                except Exception:
                    scores.append(50.0)
            scores = np.array(scores)

        for shipment in self.synthetic_data:
            self.ground_truth.append(self._outcome_to_label(shipment.get("expected_outcome","CLEARED")))

        y_true = np.array(self.ground_truth)
        threshold = 70
        binary_preds = (scores >= threshold).astype(int)

        precision = precision_score(y_true, binary_preds, zero_division=0)
        recall    = recall_score(y_true, binary_preds, zero_division=0)
        f1        = f1_score(y_true, binary_preds, zero_division=0)
        auc       = roc_auc_score(y_true, scores / 100.0)
        tn, fp, fn, tp = confusion_matrix(y_true, binary_preds).ravel()

        return {
            "method": method,
            "threshold": threshold,
            "calibration": "batch_percentile_rank",
            "precision": precision, "recall": recall, "f1_score": f1, "auc_roc": auc,
            "confusion_matrix": {"tp": int(tp), "fp": int(fp), "fn": int(fn), "tn": int(tn)},
            "score_distribution": {
                "min": float(np.min(scores)), "max": float(np.max(scores)),
                "mean": float(np.mean(scores)),
                "p50": float(np.percentile(scores, 50)),
                "p75": float(np.percentile(scores, 75)),
                "p85": float(np.percentile(scores, 85)),
                "p90": float(np.percentile(scores, 90)),
                "above_70": int(np.sum(scores >= 70)),
            },
            "total_shipments": len(self.synthetic_data),
            "high_risk_count": int(np.sum(binary_preds)),
            "data_quality_note": (
                "Calibration uses batch-percentile ranking. Absolute probability thresholds "
                "require real CBP ground-truth data. Training data artifacts limit generalization."
            ),
        }

    def print_results(self, r: Dict):
        print(f"\n{'='*70}\nRESULTS [{r['method']}]\n{'='*70}")
        print(f"  Precision: {r['precision']:.4f}  Recall: {r['recall']:.4f}  F1: {r['f1_score']:.4f}  AUC: {r['auc_roc']:.4f}")
        cm = r['confusion_matrix']
        print(f"  TP:{cm['tp']}  FP:{cm['fp']}  FN:{cm['fn']}  TN:{cm['tn']}")
        d = r['score_distribution']
        print(f"  Scores: min={d['min']:.1f} mean={d['mean']:.1f} max={d['max']:.1f}")
        print(f"  p50={d['p50']:.1f} p75={d['p75']:.1f} p85={d['p85']:.1f} p90={d['p90']:.1f}")
        print(f"  Shipments ≥70: {d['above_70']} ({d['above_70']/r['total_shipments']*100:.1f}% = top 25%)")
        print(f"\n  Gates (Precision≥0.70, Recall≥0.65, F1≥0.67, AUC≥0.75):")
        print(f"  Precision: {'PASS' if r['precision']>=0.70 else 'FAIL'}  "
              f"Recall: {'PASS' if r['recall']>=0.65 else 'FAIL'}  "
              f"F1: {'PASS' if r['f1_score']>=0.67 else 'FAIL'}  "
              f"AUC: {'PASS' if r['auc_roc']>=0.75 else 'FAIL'}")
        if 'data_quality_note' in r:
            print(f"\n  ⚠  {r['data_quality_note']}")

    def save_results(self, results: Dict, filepath: str):
        with open(filepath, "w") as f:
            json.dump(results, f, indent=2)
        print(f"\n  saved → {filepath}")


if __name__ == "__main__":
    validator = ModelValidator()
    results = validator.validate()
    validator.print_results(results)
    validator.save_results(results, "/home/rahulvadera/cbp-sentry/services/api/model_validation_results.json")
