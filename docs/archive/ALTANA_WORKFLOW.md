# Altana API Integration Workflow

## Overview
Altana supply chain verification is integrated into the comprehensive risk scoring pipeline to validate high-risk shipments against real supply chain data.

---

## 1. ALTANA API CALL POINTS IN CODE

### **Primary Integration: `/api/risk-scoring/comprehensive` (Line 877-931)**

**File**: `services/api/main.py` → `_calculate_comprehensive_risk()` function

**Workflow Flow**:
```
1. Calculate initial risk score from 17 risk components
   ↓
2. Check if score >= 80 (ALTANA_RISK_THRESHOLD)
   ↓
3. YES → Call Altana API for supply chain verification
   ↓
4. Altana Response:
   - Validates shipping parties (shipper, consignee)
   - Checks supply chain opacity
   - Returns sanctions exposure risk
   - Provides confidence score
   ↓
5. Model Refinement:
   - If Altana strongly agrees (confidence >= 90%): ✓ Uphold score
   - If Altana disputes (says "clear"): ↓ Reduce by 15 points
   - If partial agreement: ↓ Reduce by 5 points
   ↓
6. Return final_score with audit trail
```

**Code Location** (lines 877-931):
```python
# ALTANA VALIDATION: If score >= 80, query Altana for supply chain verification
if total_score >= 80:
    try:
        # Call Altana API for supply chain risk verification
        altana_response = await altana_client.validate_shipment(
            shipment_id=shipment_id,
            shipper=shipper,
            shipper_country=shipper_country,
            consignee=consignee,
            consignee_country=consignee_country,
            vessel=vessel_name,
            vessel_imo=vessel_imo
        )
        
        # Model refinement based on Altana agreement
        if altana_response and altana_response.get("confidence", 0) >= 90:
            # Altana strongly agrees with high-risk assessment
            audit_trail["altana_response"] = altana_response
            audit_trail["altana_confidence"] = altana_response.get("confidence")
            audit_trail["model_adjustment"] = 0
            reason = "Altana validated high supply chain risk"
        elif altana_response and altana_response.get("recommendation") == "CLEAR":
            # Altana disputed risk assessment - supply chain verified
            audit_trail["model_adjustment"] = -15
            reason = "Altana disputed risk assessment - supply chain verified"
        else:
            # Partial validation
            audit_trail["model_adjustment"] = -5
            reason = "Altana partial validation"
```

### **Secondary Integration: Referral Package Generation (Line 1224)**

**File**: `services/api/main.py` → `_build_referral_package()` function (Line 1220-1240)

**Purpose**: Generate Altana findings for high-risk cases (risk >= 75%)

```python
if risk_score >= ALTANA_RISK_THRESHOLD:
    altana_findings = await altana_client.verify_shipment(
        shipment_id=shipment_id,
        # ... shipment details
    )
```

### **Tertiary Integration: Atlas Verification Endpoint (Line 3064)**

**File**: `services/api/main.py` → `@app.post("/api/verify/altana")`

**Purpose**: Manual trigger for Altana verification on demand

```python
@app.post("/api/verify/altana")
async def trigger_altana_verification(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Trigger Altana Atlas supply chain verification for high-risk shipments (score ≥ 90%)."""
    shipment_id = payload.get("shipment_id")
    result = await altana_client.verify_shipment(shipment_id)
    return result
```

---

## 2. ALTANA CONFIGURATION

**File**: `services/api/altana_integration.py`

```python
ALTANA_API_KEY = os.getenv("ALTANA_API_KEY", "demo-key-12345")
ALTANA_BASE_URL = "https://api.altanaai.com/api/v1"
ALTANA_ENABLED = os.getenv("ALTANA_ENABLED", "false").lower() == "true"
ALTANA_RISK_THRESHOLD = 75.0  # Only verify shipments with risk_score >= 75%
```

**Environment Variables Required**:
- `ALTANA_ENABLED=true` (to activate)
- `ALTANA_API_KEY=your-api-key` (from Altana)

---

## 3. AUDIT TRAIL OUTPUT

Every comprehensive risk scoring response includes Altana decision data:

```json
{
  "audit_trail": {
    "initial_score": 85.0,
    "altana_query": true,
    "altana_confidence": 92.0,
    "altana_response": {
      "risk_factors": ["supply_chain_opacity", "sanctions_exposure"],
      "recommendation": "REVIEW",
      "supply_chain_opacity": 45,
      "sanctions_exposure": true
    },
    "model_adjustment": 0,
    "final_risk_score": 85.0,
    "adjustment_reason": "Altana validated high supply chain risk"
  }
}
```

---

## 4. VISUALIZATION IN UI

**Location**: V2InvestigationsPage → ReferralTab section

Shows Altana findings when available:
- Supply chain verification status
- Sanctions exposure flag
- Confidence score
- Recommendation (CLEAR / REVIEW / FLAG)

---

## NEXT STEPS

### Remove Pre-Stored risk_score
- Make risk scoring **on-demand only** via `/api/risk-scoring/comprehensive`
- Remove `risk_score` column from shipments table (keep only h1_score, h2_score, h3_score)
- Calculate dynamically at query time

### Seed Data with Varied Profiles
- **95%+ risk**: Multiple red flags (Element 9 mismatch, high AD/CVD, shipper age 0 months, OFAC match)
- **60-70% risk**: Medium indicators (dwell anomaly, new shipper, corridor risk)

See DATA_SEEDING.md for implementation details.
