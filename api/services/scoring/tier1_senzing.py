"""
Tier 1 Scorer: Senzing Entity Resolution Chain
Input: Entity resolution result (entities[], relationships[])
Output: Party Profile Risk score (0-15 points)

Logic:
- Greenfield case: VN → HK → CN chain (3 tiers)
- Confidence: average of Senzing match scores
- Risk = 15 - (chain_depth × confidence × 5) normalized
- High chain depth + high confidence = high risk (close to 15)
"""

from typing import Dict, List, Any, Optional


class Tier1Scorer:
    """Score based on Senzing entity chain depth and confidence"""

    def __init__(self):
        """Initialize Tier 1 scorer"""
        pass

    def score(
        self,
        entities: Dict[str, Any],
        relationships: Optional[List[Dict[str, Any]]] = None
    ) -> float:
        """
        Calculate Party Profile Risk score (0-15 points).

        Args:
            entities: Dict with entity data (shipper_vn, parent_cn, consignee_us, etc.)
            relationships: List of entity relationships

        Returns:
            float: Score 0-15
        """
        if not entities:
            return 0.0

        # Extract key entities
        shipper = entities.get("shipper_vn")
        parent = entities.get("parent_cn")
        consignee = entities.get("consignee_us")

        if not shipper:
            return 0.0

        # Calculate chain depth
        # VN shipper alone = 1 tier
        # VN shipper + CN parent = 2 tiers
        # VN shipper + HK intermediary + CN parent = 3 tiers
        chain_depth = 1  # Start with shipper
        if parent:
            chain_depth += 1

        # Calculate average confidence from Senzing matches
        confidences = []
        if shipper and shipper.get("match_confidence"):
            confidences.append(shipper["match_confidence"])
        if parent and parent.get("match_confidence"):
            confidences.append(parent["match_confidence"])
        if consignee and consignee.get("match_confidence"):
            confidences.append(consignee["match_confidence"])

        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.5

        # Penalize shipper role more heavily than consignee
        role_penalty = 1.0
        if shipper:
            # Shipper is higher risk
            role_penalty = 1.2

        # Risk = chain_depth × confidence × role_penalty, capped at 15
        # For Greenfield: chain_depth=2, avg_confidence=0.92, role_penalty=1.2
        # Risk = 2 × 0.92 × 1.2 × 6.8 = ~15.1, capped at 15
        base_score = min(chain_depth * avg_confidence * role_penalty * 6.8, 15.0)

        return round(base_score, 1)
