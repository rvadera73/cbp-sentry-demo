# Exact Code Changes Required for Consolidation

**File:** `services/api/main.py`

---

## Change 1: Remove Old Scorer Imports (Lines 28-29)

### BEFORE:
```python
25 from external_apis.h1_adapters import OpenCorporatesAdapter, ComtradeAdapter, ITCTariffsAdapter
26 from external_apis.h2_adapters import AISAdapter, PortAuthorityAdapter
27 from external_apis.ofac_service import ofac_service, OFACMatch
28 from ml_scorers import H1CorridorRiskScorer, H2AnomalyScorer        ❌ DELETE THIS LINE
29 from h3_scorer import H3IntelligenceScorer                           ❌ DELETE THIS LINE
30 from ingest_parser import parse_excel_manifest
```

### AFTER:
```python
25 from external_apis.h1_adapters import OpenCorporatesAdapter, ComtradeAdapter, ITCTariffsAdapter
26 from external_apis.h2_adapters import AISAdapter, PortAuthorityAdapter
27 from external_apis.ofac_service import ofac_service, OFACMatch
30 from ingest_parser import parse_excel_manifest
```

---

## Change 2: Remove Old Scorer Instantiations (Lines 135-137)

### BEFORE:
```python
134 # Initialize scorers
135 h1_scorer = H1CorridorRiskScorer()      ❌ DELETE THIS LINE
136 h2_scorer = H2AnomalyScorer()           ❌ DELETE THIS LINE
137 h3_scorer = H3IntelligenceScorer()      ❌ DELETE THIS LINE
138 
139 # Initialize comprehensive risk scoring engine
140 risk_scoring_engine = RiskScoringEngine()  ✓ KEEP THIS
```

### AFTER:
```python
134 # Initialize comprehensive risk scoring engine
135 risk_scoring_engine = RiskScoringEngine()
```

---

## Change 3: Find and Remove Three-Level Scoring Endpoint

**Locate:** Search for `async def score_shipment_three_level` or `@router.post.*three.level`

### BEFORE (around line 2950-3005):
```python
@router.post("/score/three-level/{shipment_id}", ...)
async def score_shipment_three_level(
    shipment_id: str,
    shipper_name: str = Query(...),
    shipper_country: str = Query(...),
    consignee_name: str = Query(...),
    consignee_country: str = Query(...),
    hs_code: str = Query(...),
    declared_value_usd: float = Query(...),
    declared_weight_kg: float = Query(...),
    vessel_name: Optional[str] = Query(None),
) -> Dict[str, Any]:
    """
    Score a shipment across three levels:
    Level 1: Corridor Risk (macro-level trade analysis)
    Level 2: Vessel Risk (pre-manifest anomalies)
    Level 3: Manifest Risk (transaction-level validation)
    """
    from three_level_scorer import scorer      ❌ DELETE ENTIRE FUNCTION
    from feedback_engine import feedback_engine
    
    try:
        # Get corridor-specific weights or defaults
        corridor_key = f"{shipper_country}-{consignee_country}"
        weights = feedback_engine.get_weight_configuration(corridor=corridor_key)

        # Run three-level scoring
        result = await scorer.score_shipment(
            shipment_id=shipment_id,
            shipper_name=shipper_name,
            shipper_country=shipper_country,
            consignee_name=consignee_name,
            consignee_country=consignee_country,
            hs_code=hs_code,
            declared_value_usd=declared_value_usd,
            declared_weight_kg=declared_weight_kg,
            vessel_name=vessel_name,
            corridor_weights={...},
        )

        # Update shipment record with new score
        async with await get_data_service_client() as client:
            await client.patch(f"/shipments/{shipment_id}", json={...})

        return result

    except Exception as e:
        logger.error(f"Three-level scoring error for {shipment_id}: {e}")
        return {"error": str(e), ...}
```

### AFTER:
**Delete the entire function.** The new `/api/score/full-breakdown/{id}` endpoint will replace it (see PHASE1_IMPLEMENTATION_PLAN.md for the new implementation).

---

## Change 4: Check feedback_engine.py for Old References

**File:** `services/api/feedback_engine.py`

### Command to check:
```bash
grep -n "three_level_scorer\|h3_scorer\|ml_scorers\|H1CorridorRiskScorer\|H2AnomalyScorer\|H3IntelligenceScorer" services/api/feedback_engine.py
```

If found, replace with references to `RiskScoringEngine` instead.

---

## Summary of Changes

| Change | File | Lines | Action |
|--------|------|-------|--------|
| 1 | `main.py` | 28-29 | Delete old scorer imports |
| 2 | `main.py` | 135-137 | Delete old scorer instantiations |
| 3 | `main.py` | ~2950-3005 | Delete entire three-level endpoint function |
| 4 | `feedback_engine.py` | various | Update references if found |

---

## Testing After Changes

```bash
# 1. Check for syntax errors
python -m py_compile services/api/main.py

# 2. Check for orphaned imports
grep -r "three_level_scorer\|h3_scorer\|ml_scorers" . \
  --include="*.py" --include="*.ts" --include="*.tsx"

# 3. Run tests
cd api && pytest tests/test_risk_scoring.py -v
```

---

## Using the Cleanup Script

After making these manual changes:

```bash
cd /home/rahulvadera/cbp-sentry
bash CLEANUP_SCRIPT.sh --confirm
```

This will:
1. ✓ Delete the 5 old scoring files
2. ✓ Verify no orphaned imports remain
3. ✓ Confirm only RiskScoringEngine is used

---

## Important Notes

- **Keep** `risk_scoring_engine.py` - This is the source of truth
- **Keep** `risk_models.py` - Contains all configuration
- **Delete** the three_level_scorer endpoint - Will be replaced by new `/api/score/full-breakdown/{id}`
- **Delete** old scorer instantiations - No longer needed

---

## Next Step

After cleanup, follow **PHASE1_IMPLEMENTATION_PLAN.md** to:
1. Create new `/api/services/risk_scoring/routes.py`
2. Create `/api/score/full-breakdown/{id}` endpoint
3. Update Investigation Page UI
4. Test end-to-end

