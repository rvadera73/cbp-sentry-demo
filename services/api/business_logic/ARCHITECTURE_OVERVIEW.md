# Risk Corridor Business Logic — Architecture Overview

## Executive Summary

A **Domain-Driven Design** business logic engine that automatically classifies shipments into Risk Corridors and computes domain-specific metrics for duty evasion detection. The system requires zero manual configuration and operates entirely on data-driven thresholds.

**Architecture Pattern**: Modular pipeline with orchestrated analyzers  
**Domain Model**: Risk Corridor (HTS Segment × Geographic Route × Supplier Entity)  
**Total Modules**: 5 (Classification, Volumetric, Temporal, Transshipment, Factory)  
**Integration**: FastAPI endpoints (4 new routes)

---

## System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    SHIPMENT INPUT STREAM                    │
│  {hts_code, origin, destination, shipper, weight, value}    │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
         ┌─────────────────────────────────────┐
         │  RiskCorridorFactory Orchestrator   │
         │  - Routes shipments to analyzers    │
         │  - Synthesizes composite score      │
         └────────────┬────────────────────────┘
                      │
         ┌────────────┴────────────┐
         │                         │
         ▼                         ▼
  ┌──────────────┐        ┌──────────────────────┐
  │ Create Base  │        │ Group by Corridor ID │
  │ Corridor     │        └──────────────────────┘
  │ (HTS + Route)│
  └──────┬───────┘
         │
         ▼
  ┌─────────────────────────────────────────────────────────────┐
  │                 ANOMALY DETECTION PIPELINE                  │
  │                                                               │
  │  ┌──────────────────────────────────────────────────────┐  │
  │  │ Module 1: HTS Classifier                            │  │
  │  │ ├─ Industry segment mapping (Solar, Steel, etc.)    │  │
  │  │ ├─ AD/CVD country tracking                         │  │
  │  │ ├─ Known evasion origin shifts (CN→VN routes)      │  │
  │  │ ├─ Baseline production capacity                    │  │
  │  │ └─ Duty rates (0–374%)                            │  │
  │  └─────────────────┬────────────────────────────────┘  │
  │                    │                                     │
  │  ┌─────────────────▼────────────────────────────────┐  │
  │  │ Module 2: Volumetric Delta Calculator            │  │
  │  │ ├─ Aggregate manifest volume per corridor        │  │
  │  │ ├─ Compare vs baseline annual capacity           │  │
  │  │ ├─ Compute ratio (manifest÷period_capacity)      │  │
  │  │ ├─ Detect unit price outliers                    │  │
  │  │ └─ Flag frequency spikes                         │  │
  │  │                                                   │  │
  │  │ SIGNALS: Status (FLAGGED if ratio>3),            │  │
  │  │          Severity (CRITICAL if ratio>4)          │  │
  │  └─────────────────┬────────────────────────────────┘  │
  │                    │                                     │
  │  ┌─────────────────▼────────────────────────────────┐  │
  │  │ Module 3: Temporal Analyzer                      │  │
  │  │ ├─ Calculate YoY surge (% change)                │  │
  │  │ ├─ Detect seasonal anomalies                     │  │
  │  │ ├─ Analyze trend direction (linear regression)  │  │
  │  │ ├─ Detect cyclical patterns (regular schedules) │  │
  │  │ └─ Flag growth campaigns (consecutive UPs)       │  │
  │  │                                                   │  │
  │  │ SIGNALS: Volume surge %, Surge status (CRITICAL  │  │
  │  │          if >250%), Trend direction              │  │
  │  └─────────────────┬────────────────────────────────┘  │
  │                    │                                     │
  │  ┌─────────────────▼────────────────────────────────┐  │
  │  │ Module 4: Transshipment Detector                 │  │
  │  │ ├─ FTZ dwell anomaly (flag if >3× baseline)     │  │
  │  │ ├─ Port routing anomaly (return visits, hubs)   │  │
  │  │ ├─ Consolidation pattern (5+ origins in FTZ)    │  │
  │  │ ├─ Vessel rotation pattern (many port pairs)    │  │
  │  │ └─ Composite transshipment risk score           │  │
  │  │                                                   │  │
  │  │ SIGNALS: FTZ dwell ratio, Hub transit flags,     │  │
  │  │          Consolidation detected, Risk level      │  │
  │  └─────────────────┬────────────────────────────────┘  │
  │                    │                                     │
  └────────────────────┼──────────────────────────────────┘
                       │
                       ▼
  ┌─────────────────────────────────────────────────────┐
  │  Module 5: Risk Corridor Factory                    │
  │  ├─ Synthesize composite risk score (0-100)       │
  │  │  - 20% baseline (industry + evasion routes)    │
  │  │  - 40% volumetric delta                        │
  │  │  - 20% YoY surge                               │
  │  │  - 10% price anomalies                         │
  │  │  - 10% transshipment risk                      │
  │  │                                                 │
  │  ├─ Classify risk level                           │
  │  │  - CRITICAL (score ≥ 75 or ≥ 3 signals)       │
  │  │  - HIGH (score ≥ 50 or ≥ 2 signals)           │
  │  │  - MEDIUM (score ≥ 25 or ≥ 1 signal)          │
  │  │  - LOW (score < 25)                            │
  │  │                                                 │
  │  └─ Return enriched corridor object               │
  └────────┬────────────────────────────────────────┘
           │
           ▼
  ┌────────────────────────────────────────────────────┐
  │           ENRICHED CORRIDOR OUTPUT                 │
  │                                                    │
  │ {                                                  │
  │   "corridor_id": "HC-8541-CNUS-A1B2",             │
  │   "industry_segment": "Solar Infrastructure",     │
  │   "shipment_count": 47,                           │
  │   "composite_risk_score": 72.5,                   │
  │   "risk_level": "HIGH",                           │
  │   "macro_volumetric_delta": {...},                │
  │   "yoy_surge": {...},                             │
  │   "price_anomalies": {...},                       │
  │   "transshipment_risk": {...}                     │
  │ }                                                  │
  └────────────────────────────────────────────────────┘
           │
           ▼
  ┌────────────────────────────────────────────────────┐
  │  API LAYER - FastAPI Endpoints                     │
  │                                                    │
  │  GET  /api/risk-corridors                         │
  │  GET  /api/risk-corridors/{corridor_id}           │
  │  POST /api/risk-corridors/classify                │
  │  GET  /api/risk-corridors/hts/{hts_code}          │
  └────────────────────────────────────────────────────┘
```

---

## Module Relationships

```
                    ┌─────────────────────┐
                    │ RiskCorridorFactory │
                    │   (Orchestrator)    │
                    └─────────────────────┘
                            │
            ┌───────────────┼───────────────┐
            ▼               ▼               ▼
      ┌──────────┐    ┌──────────┐    ┌──────────┐
      │   HTS    │    │Volumetric│    │ Temporal │
      │Classifier│    │ Analyzer │    │Analyzer  │
      └──────────┘    └──────────┘    └──────────┘
            │               │               │
            └───────────────┼───────────────┘
                            │
                   ┌────────▼────────┐
                   │ Transshipment   │
                   │ Detector        │
                   └────────┬────────┘
                            │
                   Composite Score ◄──── Factory Synthesis
```

---

## Data Flow Example: China Solar Panel Shipments

### Input: 47 Shipments in One Week

```json
[
  {
    "hts_code": "8541.40.60",
    "origin_country": "CN",
    "destination_country": "US",
    "shipper_name": "Beijing Sunpower Ltd",
    "declared_value_usd": 250000,
    "declared_weight_kg": 15000,
    "vessel_name": "Ever Given",
    "filing_date": "2026-05-20"
  },
  ... 46 more ...
]
```

### Processing Flow

**Step 1: HTS Classification**
```
HTS 8541.40.60
  ├─ Segment: "Solar Infrastructure"
  ├─ Baseline capacity: 2.5M tons/year = 47,940 tons/week
  ├─ AD/CVD countries: ["CN", "VN", "TH", "MY"]
  ├─ Evasion routes: ["VN", "MY", "TH", "KH"]
  ├─ Duty rate (CN): 100%
  └─ Baseline risk score: 60/100
```

**Step 2: Grouping**
```
Corridor ID: HC-8541-CNUS-8A3F
  ├─ HTS chapter: 8541
  ├─ Route: China → USA
  ├─ Shipper hash: 8A3F (from "Beijing Sunpower Ltd")
  └─ Shipment count: 47
```

**Step 3: Volumetric Analysis**
```
Total manifest volume: 47 × 15,000 kg = 705,000 kg = 705 tons
Period capacity: 47,940 tons
Ratio: 705 ÷ 47,940 = 1.47× (NORMAL — within capacity)
```

**Step 4: Temporal Analysis**
```
Prior week shipments: 10
Current week shipments: 47
Volume surge: (47-10) ÷ 10 × 100 = 370% (CRITICAL)
Status: CRITICAL surge
```

**Step 5: Price Analysis**
```
Unit prices: 250,000 ÷ 15 = $16,667/ton (consistent across all)
Std dev: 0 (no outliers)
Anomaly: NOT DETECTED
```

**Step 6: Transshipment Detection**
```
FTZ codes in shipments: None (hypothetical)
Port routing: Standard CN → US
Consolidation: No consolidation pattern
Risk score: 0/100
```

**Step 7: Composite Scoring**
```
Baseline risk (20%):     60 × 0.20 = 12
Volumetric (40%):        1.47 × 40 = ~20
YoY surge (20%):         370% → 20
Price anomalies (10%):   0 × 0.10 = 0
Transshipment (10%):     0 × 0.10 = 0
                         ─────────────
Total composite score: 52/100

Risk classification: HIGH (2 high-signal indicators)
```

### Output: Enriched Corridor

```json
{
  "corridor_id": "HC-8541-CNUS-8A3F",
  "hts_chapter": "8541",
  "industry_segment": "Solar Infrastructure",
  "origin_country": "CN",
  "destination_country": "US",
  "supplier_entity": "Beijing Sunpower Ltd",
  
  "shipment_count": 47,
  "aggregate_value_usd": 11750000,
  "total_weight_tons": 705,
  "active_vessels": 1,
  
  "macro_volumetric_delta": {
    "status": "NORMAL",
    "ratio": 1.47,
    "severity": "MEDIUM",
    "signal": "Outbound volume 1.47× estimated production capacity"
  },
  
  "yoy_surge": {
    "volume_surge_pct": 370,
    "surge_status": "CRITICAL",
    "signal": "Volume surge 370% 7-day (47 vs 10 shipments)"
  },
  
  "price_anomalies": {
    "anomaly_detected": false,
    "average_unit_price_per_ton": 16667
  },
  
  "transshipment_risk": {
    "risk_level": "LOW",
    "signals": []
  },
  
  "composite_risk_score": 52.0,
  "risk_level": "HIGH",
  "last_updated": "2026-05-20T14:32:15"
}
```

---

## Risk Scoring Formula

### Composite Risk Score (0-100)

```
Score = 
  (Baseline Risk × 0.20) +
  (Volumetric Score × 0.40) +
  (Surge Score × 0.20) +
  (Price Anomaly Score × 0.10) +
  (Transshipment Score × 0.10)
```

### Component Scoring

#### Baseline Risk (20%)
```
Base = 40 points (high-risk commodity)
Evasion bonus = 10 points × count of known evasion routes
Ceiling = 100 points
```

#### Volumetric Score (40%)
```
If status == "FLAGGED":
  Score = 10 + (ratio × 5)  [capped at 40]
Else:
  Score = ratio × 5
```

#### Surge Score (20%)
```
If CRITICAL (surge > 250%):  Score = 20
If HIGH (surge > 150%):      Score = 15
If MEDIUM (surge > 75%):     Score = 8
Else:                        Score = min(8, surge% / 50)
```

#### Price Anomaly Score (10%)
```
If anomaly_detected:  Score = 10
Else:                 Score = 0
```

#### Transshipment Score (10%)
```
Score = (transshipment_risk_score × 0.1)
```

### Risk Level Classification

```
if composite_score >= 75 OR high_signals >= 3:
    risk_level = "CRITICAL"
elif composite_score >= 50 OR high_signals >= 2:
    risk_level = "HIGH"
elif composite_score >= 25 OR high_signals >= 1:
    risk_level = "MEDIUM"
else:
    risk_level = "LOW"
```

---

## Threshold Tuning

All thresholds are configurable via class constants:

```python
# VolumetricAnalyzer
RATIO_CRITICAL = 4.0  # Flag if 4× capacity
RATIO_HIGH = 3.0      # Flag if 3× capacity
RATIO_MEDIUM = 2.0    # Medium risk if 2× capacity

# TemporalAnalyzer
SURGE_CRITICAL = 250  # 250% surge = CRITICAL
SURGE_HIGH = 150      # 150% surge = HIGH
SURGE_MEDIUM = 75     # 75% surge = MEDIUM

# TransshipmentDetector
FTZ_DWELL_CRITICAL = 3.0  # 3× baseline = CRITICAL
FTZ_DWELL_MEDIUM = 1.5    # 1.5× baseline = MEDIUM
```

Analyst can override per-corridor via:
- `corridor_factory.hts_classifier.INDUSTRY_MAP["8541"]["baseline_annual_capacity_tons"]`
- Time period window in `aggregate_corridor_metrics(time_period_days=30)`

---

## Performance Characteristics

| Operation | Complexity | Time (10K shipments) |
|-----------|-----------|----------------------|
| Create corridor from shipment | O(1) | <1ms |
| Group by corridor | O(n) | 100ms |
| Aggregate single corridor | O(m) | 5-10ms (m = shipments in corridor) |
| Full pipeline (group + aggregate) | O(n) | 500-800ms |
| API query (all corridors) | O(n) | 1-2s (includes DB + pipeline) |

---

## Integration Checklist

- [x] Module 1: HTS classifier (independent)
- [x] Module 2: Volumetric analyzer (depends on HTS classifier for capacity)
- [x] Module 3: Temporal analyzer (independent)
- [x] Module 4: Transshipment detector (independent)
- [x] Module 5: Factory (orchestrates all)
- [x] API layer (4 endpoints)
- [x] Test suite (20+ tests)
- [x] Documentation (README, examples, architecture)

---

## Future Enhancements

### Phase 2: Machine Learning
- Train classifier on historical evasion cases
- Learn dynamic thresholds per corridor
- Detect network effects (supplier rings)

### Phase 3: Predictive Risk
- Forecast next-period volume based on trends
- Alert on early warning signals
- Confidence intervals on predictions

### Phase 4: Analyst Feedback Loop
- Record analyst overrides
- Learn weight adjustments per sector
- A/B test threshold changes

---

## References

- **CBP Priority Trade Corridors**: HTS chapters 8541 (Solar), 7604 (Aluminum), 7210 (Steel)
- **AD/CVD Databases**: USITC, Commerce Department
- **FTZ Baselines**: CBP Port Authority data
- **Transshipment Hubs**: Regional trade flow analysis (Singapore, Dubai, Malaysia)
