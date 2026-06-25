# CBP Sentry — Risk Scoring Architecture
**Version:** 2.0 (June 2026)  
**Status:** Authoritative Reference  
**Supersedes:** RISK_SCORING_REDESIGN_V3_HYBRID.md, COMPLETE_RISK_MODEL_SERVICE_DESIGN.md, README_RISK_SCORING.md

---

## 1. Core Design Principles

### 1.1 Model Maturity vs Score Range — They Are Different Things

> **Critical distinction:** Model maturity controls the *confidence interval* (precision) of the score, not the *range* (0–100) of achievable scores.

| Maturity | Score Range | Confidence Interval | What it means |
|---|---|---|---|
| 15% | 0 – 100 | ± 17 pts | "I think 82, but could be 65–99" |
| 50% | 0 – 100 | ± 10 pts | "I think 82, could be 72–92" |
| 90% | 0 – 100 | ± 2 pts  | "I think 82, almost certainly 80–84" |

A 15%-mature model **CAN** produce a score of 90+. It just has a wider uncertainty band.

**What was wrong before (v1):** The XGBoost model was used as the *primary score* and its training distribution was compressed (30–51), making 90+ scores impossible. This was a training data problem, not a maturity concept.

---

## 2. Scoring Architecture (v2)

### 2.1 Three-Layer Stack

```
┌──────────────────────────────────────────────────────────────────┐
│  Layer 1: Rule Engine (Deterministic, Full 0–100 Range)          │
│  • 18 components across 7 risk factors                           │
│  • Reads enriched features directly from DB                      │
│  • Produces subtotal via weighted sum                            │
├──────────────────────────────────────────────────────────────────┤
│  Layer 2: Compound Risk Multiplier                               │
│  • Counts co-occurring critical indicators (0–5+)                │
│  • Non-additive compounding: 5 indicators → ×1.50               │
│  • Reflects that simultaneous red flags multiply risk, not add  │
├──────────────────────────────────────────────────────────────────┤
│  Layer 3: ML Adjustment Delta (Maturity-Weighted)                │
│  • XGBoost output = adjustment delta (±0–15 pts), not the score  │
│  • Delta weight = model_maturity / 100                          │
│  • At 15% maturity: ±small delta. At 90%: ±larger delta         │
└──────────────────────────────────────────────────────────────────┘
                            │
                    Final Score (0–100)
              + Confidence Interval (maturity-based)
```

### 2.2 Scoring Formula

```python
# Step 1: 18-component rule engine
subtotal = sum(component.score/10 * component.weight for component in components)

# Step 2: Compound multiplier for co-occurring critical indicators
n_indicators = len(check_critical_indicators(shipment))
multiplier = {0:1.0, 1:1.0, 2:1.10, 3:1.20, 4:1.35, 5+:1.50}[n_indicators]
rule_engine_score = min(subtotal * multiplier, 100)

# Step 3: ML adjustment delta (maturity-weighted, not primary)
xgb_delta = (xgb_score - 50) * (maturity/100) * 0.30
final_score = min(max(rule_engine_score + xgb_delta, 0), 100)

# Step 4: Confidence interval (maturity-aware)
confidence_interval = ±round(20 * (1 - maturity/100))
```

---

## 3. The 7 Risk Factors (Rule Engine)

| Factor | Weight | Key Components |
|---|---|---|
| **Documentation** | ~23% | Element 9 origin mismatch (highest), ISF amendments, manifest completeness |
| **Commodity** | ~14% | AD/CVD rate exposure*, export controls, UFLPA forced labor |
| **Routing** | ~12% | AIS dwell time anomaly*, transshipment hub selection, vessel flag |
| **Party** | ~14% | Shipper age & establishment*, compliance history, OFAC exposure |
| **Corridor** | ~18% | Country-of-origin risk, tariff evasion incentive |
| **Pattern** | ~9%  | Unit price vs benchmark*, transshipment ML pattern |
| **Time** | ~9%  | Time sensitivity indicators |

*= reads directly from enriched DB columns (fixed in v2)

### 3.1 Critical Feature Reads (v2 Fix)

These features are read **directly from DB columns** (not from external lookups):

| Component | DB Column | Formula |
|---|---|---|
| AD/CVD Rate | `ad_cvd_rate` (decimal: 1.76=176%) | `tariff_score = min(rate*100 / 20.0, 10)` |
| AIS Dwell | `dwell_days` | `9.5 if days≥18, 7.5 if ≥12, 5.5 if ≥8, 2.5 if ≥4, 1.0` |
| Unit Price | `unit_price_per_kg` + HS-family baseline | `9.0 if variance<-50%, 6.5 if <-20%` |

Federal Register and Comtrade APIs are consulted as **enrichment sources** during data ingestion, not at scoring time.

---

## 4. Critical Indicator Auto-Escalation

Five indicators trigger compound scoring and priority escalation independently of the composite score:

| Indicator | DB Column | Threshold |
|---|---|---|
| ISF Element 9 origin mismatch | `element9_is_mismatch` | `= true` |
| High AD/CVD tariff exposure | `ad_cvd_rate` | `≥ 1.0` (100%+) |
| Excessive dwell time | `dwell_days` | `≥ 10 days` |
| Newly established shipper | `shipper_age_months` | `< 6 months` |
| Undervalued pricing | `price_variance_percent` | `≤ -40%` |

**Compound multiplier:**
- 2 indicators → ×1.10 (rule engine score)
- 3 indicators → ×1.20
- 4 indicators → ×1.35
- 5 indicators → ×1.50

**Indicator-based h1_level override** (regardless of composite score):
- 2+ indicators + any AD/CVD → at least HIGH
- element9_mismatch + AD/CVD ≥ 100% → CRITICAL floor

---

## 5. Score Distribution (After Enrichment — 1399 Shipments)

| Tier | Score Range | Count | % | Referral Eligible |
|---|---|---|---|---|
| CRITICAL | ≥ 80 | ~25 | 1.8% | ✅ Yes |
| HIGH | 65–79 | ~47 | 3.4% | ✅ Yes (weekly review) |
| MEDIUM | 50–64 | ~109 | 7.8% | ⚠️ Investigator review |
| LOW | < 50 | ~1218 | 87% | No |
| **Total** | | **1399** | 100% | |

---

## 6. Referral Threshold Policy

> **Policy: Referral threshold = score ≥ 65 OR h1_level = CRITICAL**

This replaces the previously assumed 90% threshold, which was based on synthetic seed data with no algorithmic basis.

**Justification in referral packages:**
- At 15% maturity, score of 82 ± 17 means lower bound = 65 → HIGH risk confirmed
- Referral documents list critical indicators (element9 mismatch, AD/CVD 176%, 21d dwell, 2mo shipper)
- Human investigator confirms before submission → fully defensible under EAPA statute

**Weekly 2-referral-per-week workflow:**
With 25 CRITICAL (≥80) cases in queue, there is a 12-week backlog of referral-eligible cases.
New shipments arriving weekly will generate ~2–3 new HIGH/CRITICAL cases per week (based on 1.8% + 3.4% base rate × weekly ingest volume).

---

## 7. Score Example — CRITICAL Case

```
Case: DEMO-VN-CRITICAL-001 (Aluminum extrusions, VN→US)

Rule Engine Components (selected):
  Element 9 Mismatch (VN→CN):    9.5/10 × 11.4%  =  10.8 pts
  AD/CVD 176%:                   8.8/10 × 6.8%   =   6.0 pts
  Dwell 21 days (CRITICAL):      9.5/10 × 5.5%   =   5.2 pts
  Shipper Age 2 months:          9.0/10 × 4.8%   =   4.3 pts
  VN Corridor Risk:              8.0/10 × 10.9%  =   8.8 pts
  Unit Price -85% benchmark:     9.0/10 × 4.5%   =   4.1 pts
  Other components (12):                          =  13.9 pts
                                               ─────────────
  Rule Engine Subtotal:                           =  53.1 pts

  Compound Multiplier (4 indicators):             × 1.35
  Rule Engine Score:                              = 71.8 pts

  ML Adjustment (XGBoost, 15% maturity):          + 0.0 pts
  AIS Dwell Corroboration:                        +14.3 pts
  Final Score:                                    = 86.1 / 100

  Confidence Interval (15% maturity):             ± 17 pts
  Effective range:                                [69, 100]
  → Case classified: CRITICAL ✅
```

---

## 8. Model Maturity Gates

| Gate | Target | Unlock Condition |
|---|---|---|
| Gate 0 (current) | 15% | Rule engine + compound multiplier operational |
| Gate 1 | 30% | ML model trained on 300+ confirmed cases; CI ±14 |
| Gate 2 | 50% | ML model trained on 750+ cases; CI ±10; XGBoost delta meaningful |
| Gate 3 | 75% | ML primary adjuster (±15 pts); rule engine as floor; CI ±5 |
| Gate 4 | 90% | Full ML-primary scoring; rule engine for explainability only; CI ±2 |

As maturity increases:
- ML adjustment delta grows in magnitude and accuracy
- Confidence interval narrows
- Rule engine score remains the stable floor at all gates

---

## 9. Data Requirements

### 9.1 Enriched Features (required for accurate scoring)

These columns must be populated in `cbp_sentry.shipments`:

| Column | Type | Source | Notes |
|---|---|---|---|
| `ad_cvd_rate` | REAL (decimal) | Commerce CBP, seeded | 1.76 = 176% |
| `dwell_days` | REAL | AIS/vessel tracking | Actual dwell at transshipment port |
| `unit_price_per_kg` | REAL | Invoice / CBP 3461 | Declared value ÷ weight |
| `element9_is_mismatch` | BOOLEAN | ISF data / CORD entity | Origin discrepancy flag |
| `element9_declared_country` | TEXT | ISF Element 9 | Declared country of origin |
| `element9_actual_country` | TEXT | CORD entity resolution | Resolved actual country |
| `shipper_age_months` | INTEGER | CBP trader history | Months since first import |
| `price_variance_percent` | REAL | Computed | vs HS-family benchmark |

### 9.2 Feature Enrichment Script

```bash
# Enrich all shipments with realistic risk features (idempotent):
DATABASE_URL="postgresql://..." python3 scripts/enrich_shipment_features.py

# Dry-run to see distribution without writing:
python3 scripts/enrich_shipment_features.py --dry-run
```

### 9.3 Batch Re-score

After enrichment or rule engine changes, rescore all shipments:
```bash
# Via API (updates calculated_risk_score in DB):
python3 -c "
import requests
ships = requests.get('http://localhost:8000/api/shipments?limit=2000').json()['data']
for s in ships:
    requests.post('http://localhost:8000/api/risk-scoring/comprehensive', json={'shipment_id': s['id']})
"
```

---

## 10. API Endpoints

| Endpoint | Purpose |
|---|---|
| `POST /api/risk-scoring/comprehensive` | Full rule engine score with write-back to DB |
| `GET /api/shipments?limit=N&risk_min=65` | List HIGH/CRITICAL shipments for referral queue |
| `POST /api/referrals/{shipment_id}` | Generate full 14-section CSOP referral package |

---

## 11. Key Files

| File | Purpose |
|---|---|
| `services/api/risk_scoring_engine.py` | Rule engine, compound multiplier, ML delta, CI |
| `services/api/risk_scoring/routes.py` | Comprehensive scoring endpoint |
| `services/api/referral_comprehensive.py` | CSOP referral package generator |
| `scripts/enrich_shipment_features.py` | Feature enrichment for existing shipments |
| `services/data/init.sql` | DB schema including enriched feature columns |
