"""
Scoring Service: Main orchestrator for 4-tier ML scoring pipeline
Coordinates all tiers and generates final ScoreResponse
"""

from typing import Dict, Any, Optional
import sys
from pathlib import Path

# Add api directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from models.schemas import ScoreResponse
from .tier1_senzing import Tier1Scorer
from .tier2_isolation_forest import Tier2Scorer
from .tier3_lgbm import Tier3Scorer
from .tier4_bbn import Tier4Scorer
from .aggregator import ScoreAggregator
from .xai_assertions import XAIAssertionGenerator


class ScoringService:
    """Orchestrate 4-tier ML scoring pipeline"""

    def __init__(
        self,
        model_dir: Optional[str] = None
    ):
        """
        Initialize scoring service with optional model paths.

        Args:
            model_dir: Directory containing pre-trained models
        """
        # Initialize tier scorers
        self.tier1 = Tier1Scorer()
        self.tier2 = Tier2Scorer(
            model_path=f"{model_dir}/isolation_forest.pkl" if model_dir else None
        )
        self.tier3 = Tier3Scorer(
            model_path=f"{model_dir}/lgbm_classifier.txt" if model_dir else None
        )
        self.tier4 = Tier4Scorer(
            model_path=f"{model_dir}/bbn_model.pkl" if model_dir else None
        )

        # Aggregator and XAI
        self.aggregator = ScoreAggregator()
        self.xai_gen = XAIAssertionGenerator()

    def score_shipment(
        self,
        manifest: Dict[str, Any],
        entities: Dict[str, Any]
    ) -> ScoreResponse:
        """
        Score a shipment using all 4 tiers.

        Args:
            manifest: Manifest data with HTS, COO, AIS, pricing, etc.
            entities: Entity resolution results (shipper, parent, consignee, etc.)

        Returns:
            ScoreResponse with total_score, components, XAI assertions
        """
        # Tier 1: Senzing entity chain
        tier1_score = self.tier1.score(entities)

        # Tier 2: AIS anomaly detection
        tier2_score = self.tier2.score(manifest)

        # Tier 3: Commodity + pattern
        tier3_commodity, tier3_pattern = self.tier3.score(manifest)

        # Tier 4: BBN origin fraud + time sensitivity
        tier4_origin, tier4_time, bbn_posteriors = self.tier4.score(manifest, entities)

        # Generate XAI assertions
        xai_assertions_raw = self.xai_gen.generate_assertions(
            scores={
                "tier1": tier1_score,
                "tier2": tier2_score,
                "tier3_commodity": tier3_commodity,
                "tier3_pattern": tier3_pattern,
                "tier4_origin": tier4_origin,
                "tier4_time": tier4_time
            },
            manifest=manifest,
            entities=entities
        )

        # Extract text from XAI dicts
        xai_texts = [a["text"] for a in xai_assertions_raw]

        # Aggregate all scores
        response = self.aggregator.aggregate(
            tier1_score=tier1_score,
            tier2_score=tier2_score,
            tier3_commodity=tier3_commodity,
            tier3_pattern=tier3_pattern,
            tier4_origin=tier4_origin,
            tier4_time=tier4_time,
            manifest=manifest,
            entities=entities,
            bbn_posteriors=bbn_posteriors,
            xai_assertions=xai_texts
        )

        return response
