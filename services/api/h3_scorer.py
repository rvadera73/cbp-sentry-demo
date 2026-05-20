"""
H3 Intelligence Scorer - OFAC, Watch Lists, Watch List Entities, New Importer Signals
Max: 25 points
"""
import logging
from typing import Dict, Any
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class H3IntelligenceScorer:
    """Horizon 3: Full Intelligence Assessment

    Factors:
    - OFAC/SDN list hits
    - Prior EAPA involvement
    - New importer with high-value entries
    - Volume surge indicators
    """

    def __init__(self):
        self.name = "H3 Intelligence Scorer"
        self.max_score = 25

    async def score(
        self,
        shipper_name: str,
        consignee_name: str,
        declared_value: float,
        shipper_age_months: int,
        declared_weight_kg: float,
        prior_eapa_filings: int = 0,
        ofac_hit: bool = False,
        is_new_importer: bool = False,
        volume_surge_ratio: float = 1.0,
    ) -> Dict[str, Any]:
        """Score H3 intelligence factors"""

        score = 0
        factors = []

        # 1. OFAC/SDN HIT (0-15 points)
        # Shipper or consignee on OFAC Specially Designated Nationals list
        if ofac_hit:
            ofac_score = 15
            score += ofac_score
            factors.append({
                "name": "OFAC_SDN_HIT",
                "points": ofac_score,
                "description": "Entity appears on OFAC SDN list"
            })
        else:
            ofac_score = 0

        # 2. WATCH LIST / PRIOR EAPA (0-10 points)
        # Prior involvement in EAPA investigations
        if prior_eapa_filings > 0:
            if prior_eapa_filings >= 3:
                watch_score = 10
                factors.append({
                    "name": "WATCH_LIST_ENTITY",
                    "points": watch_score,
                    "prior_eapa_filings": prior_eapa_filings,
                    "description": f"Entity has {prior_eapa_filings} prior EAPA involvement"
                })
            elif prior_eapa_filings >= 1:
                watch_score = 5
                factors.append({
                    "name": "WATCH_LIST_ENTITY",
                    "points": watch_score,
                    "prior_eapa_filings": prior_eapa_filings,
                    "description": f"Entity has {prior_eapa_filings} prior EAPA involvement"
                })
            else:
                watch_score = 0
        else:
            watch_score = 0

        score += watch_score

        # 3. NEW IMPORTER WITH HIGH VOLUME (0-8 points)
        # Importer < 1 year old with high-value entries
        if is_new_importer and declared_value > 50000:
            new_importer_score = 8
            score += new_importer_score
            factors.append({
                "name": "NEW_IMPORTER_HIGH_VOL",
                "points": new_importer_score,
                "importer_age_months": shipper_age_months,
                "value_usd": declared_value,
                "description": "New importer (< 1 year) importing high-value shipment"
            })
        else:
            new_importer_score = 0

        # 4. SURGE VOLUME (0-5 points)
        # Sudden increase in import volume from entity
        if volume_surge_ratio > 3.0:
            surge_score = 5
            score += surge_score
            factors.append({
                "name": "SURGE_VOLUME",
                "points": surge_score,
                "surge_ratio": round(volume_surge_ratio, 1),
                "description": f"Import volume surge ({round(volume_surge_ratio, 1)}x baseline)"
            })
        else:
            surge_score = 0

        # Cap at max_score
        final_score = min(score, self.max_score)

        return {
            "horizon": "H3",
            "score": final_score,
            "max_score": self.max_score,
            "factors": factors,
            "breakdown": {
                "ofac_risk": ofac_score,
                "watch_list_risk": watch_score,
                "new_importer_risk": new_importer_score,
                "volume_surge_risk": surge_score,
            },
        }
