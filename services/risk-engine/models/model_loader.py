"""Model loading and management for ML components."""
import logging
import os
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
import pickle
import joblib
import xgboost as xgb
import numpy as np

logger = logging.getLogger(__name__)


class ModelLoader:
    """Handles loading and caching of trained ML models."""

    def __init__(self, models_dir: Optional[str] = None):
        """
        Initialize ModelLoader.

        Args:
            models_dir: Directory containing trained model files
        """
        # Try multiple possible paths
        candidates = [
            models_dir or os.getenv("ML_MODELS_DIR"),
            os.getenv("ML_MODELS_DATA_DIR"),
            "/app/models_data",  # Alternative mounted path in Docker
            "/home/rahulvadera/cbp-sentry/models",  # Default local path
        ]

        self.models_dir = None
        for candidate in candidates:
            if candidate and Path(candidate).exists():
                self.models_dir = Path(candidate)
                logger.info(f"Found models directory: {self.models_dir}")
                break

        if self.models_dir is None:
            # Use default
            self.models_dir = Path(candidates[0] or "/app/models_data")
            logger.warning(f"No existing models directory found, using: {self.models_dir}")

        self.xgboost_model = None
        self.isolation_forest = None
        self.shap_explainer = None
        self.feature_names = None
        self.scaler = None
        self.models_loaded = False

        logger.info(f"ModelLoader initialized with models_dir: {self.models_dir}")

    def load_all_models(self) -> bool:
        """
        Load all trained models.

        Returns:
            Success flag
        """
        try:
            logger.info("Loading all ML models...")

            # Load XGBoost
            if not self._load_xgboost():
                logger.error("Failed to load XGBoost model")
                return False

            # Load Isolation Forest
            if not self._load_isolation_forest():
                logger.error("Failed to load Isolation Forest model")
                return False

            # Load SHAP explainer
            if not self._load_shap_explainer():
                logger.warning("SHAP explainer not available, continuing without it")

            # Load scaler if available
            self._load_scaler()

            self.models_loaded = True
            logger.info("All ML models loaded successfully")
            return True

        except Exception as e:
            logger.error(f"Error loading models: {e}")
            return False

    def _load_xgboost(self) -> bool:
        """Load XGBoost model."""
        try:
            xgb_path = self.models_dir / "xgboost_model.json"
            if not xgb_path.exists():
                logger.error(f"XGBoost model not found at {xgb_path}")
                return False

            self.xgboost_model = xgb.Booster()
            self.xgboost_model.load_model(str(xgb_path))

            # Extract feature names from model
            self.feature_names = self.xgboost_model.feature_names

            logger.info(f"XGBoost model loaded: {self.xgboost_model.num_boosted_rounds()} rounds, "
                       f"{len(self.feature_names)} features")
            return True

        except Exception as e:
            logger.error(f"Error loading XGBoost: {e}")
            return False

    def _load_isolation_forest(self) -> bool:
        """Load Isolation Forest model."""
        try:
            iforest_path = self.models_dir / "isolation_forest_model.pkl"
            if not iforest_path.exists():
                logger.error(f"Isolation Forest model not found at {iforest_path}")
                return False

            self.isolation_forest = joblib.load(str(iforest_path))
            logger.info(f"Isolation Forest model loaded: {self.isolation_forest.n_estimators} estimators")
            return True

        except Exception as e:
            logger.error(f"Error loading Isolation Forest: {e}")
            return False

    def _load_shap_explainer(self) -> bool:
        """Load SHAP explainer."""
        try:
            shap_path = self.models_dir / "shap_explainer.pkl"
            if not shap_path.exists():
                logger.warning(f"SHAP explainer not found at {shap_path}")
                return False

            self.shap_explainer = joblib.load(str(shap_path))
            logger.info("SHAP explainer loaded successfully")
            return True

        except Exception as e:
            logger.warning(f"Error loading SHAP explainer: {e}")
            return False

    def _load_scaler(self) -> bool:
        """Load feature scaler if available."""
        try:
            scaler_path = self.models_dir / "scaler.pkl"
            if not scaler_path.exists():
                logger.debug("Scaler not found, will not normalize features")
                return False

            with open(scaler_path, 'rb') as f:
                self.scaler = pickle.load(f)

            logger.info("Scaler loaded successfully")
            return True

        except Exception as e:
            logger.warning(f"Error loading scaler: {e}")
            return False

    def predict_xgboost(self, features: np.ndarray) -> Tuple[np.ndarray, Optional[np.ndarray]]:
        """
        Make predictions with XGBoost.

        Args:
            features: Feature array (N x 72)

        Returns:
            Tuple of (predictions, probabilities)
        """
        if self.xgboost_model is None:
            raise ValueError("XGBoost model not loaded")

        try:
            # Create DMatrix
            dmatrix = xgb.DMatrix(features, feature_names=self.feature_names)

            # Predict probabilities
            proba = self.xgboost_model.predict(dmatrix)

            # Convert to binary predictions
            predictions = (proba >= 0.5).astype(int)

            return predictions, proba

        except Exception as e:
            logger.error(f"Error in XGBoost prediction: {e}")
            raise

    def predict_isolation_forest(self, features: np.ndarray) -> np.ndarray:
        """
        Detect anomalies with Isolation Forest.

        Args:
            features: Feature array (N x 72)

        Returns:
            Anomaly predictions (-1 for anomaly, 1 for normal)
        """
        if self.isolation_forest is None:
            raise ValueError("Isolation Forest model not loaded")

        try:
            predictions = self.isolation_forest.predict(features)
            return predictions

        except Exception as e:
            logger.error(f"Error in Isolation Forest prediction: {e}")
            raise

    def get_anomaly_scores(self, features: np.ndarray) -> np.ndarray:
        """
        Get anomaly scores from Isolation Forest.

        Args:
            features: Feature array (N x 72)

        Returns:
            Anomaly scores (negative = more anomalous)
        """
        if self.isolation_forest is None:
            raise ValueError("Isolation Forest model not loaded")

        try:
            scores = self.isolation_forest.score_samples(features)
            return scores

        except Exception as e:
            logger.error(f"Error getting anomaly scores: {e}")
            raise

    def explain_prediction(self, features: np.ndarray, prediction_index: int = None) -> Optional[Dict[str, Any]]:
        """
        Get SHAP explanation for a prediction.

        Args:
            features: Feature array
            prediction_index: Index of sample to explain (if batch)

        Returns:
            SHAP explanation data or None if explainer unavailable
        """
        if self.shap_explainer is None:
            logger.debug("SHAP explainer not available")
            return None

        try:
            # Ensure 2D array
            if features.ndim == 1:
                features = features.reshape(1, -1)

            # Get SHAP values
            shap_values = self.shap_explainer.shap_values(features)

            # Return explanation for first sample
            idx = prediction_index or 0
            return {
                "shap_values": shap_values[idx].tolist() if hasattr(shap_values[idx], 'tolist') else shap_values[idx],
                "base_value": float(self.shap_explainer.expected_value) if hasattr(self.shap_explainer, 'expected_value') else None,
                "feature_names": self.feature_names,
                "prediction_index": idx
            }

        except Exception as e:
            logger.warning(f"Error generating SHAP explanation: {e}")
            return None

    def get_model_info(self) -> Dict[str, Any]:
        """Get information about loaded models."""
        return {
            "models_loaded": self.models_loaded,
            "xgboost_loaded": self.xgboost_model is not None,
            "isolation_forest_loaded": self.isolation_forest is not None,
            "shap_explainer_loaded": self.shap_explainer is not None,
            "scaler_loaded": self.scaler is not None,
            "models_dir": str(self.models_dir),
            "feature_count": len(self.feature_names) if self.feature_names else 0,
            "feature_names": self.feature_names[:5] if self.feature_names else None
        }
