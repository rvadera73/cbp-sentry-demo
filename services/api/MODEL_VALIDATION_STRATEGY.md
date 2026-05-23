# Risk Scoring Model — Data Validation & Training Strategy

## CRITICAL GAPS IN CURRENT MODEL

### 1. No Ground Truth (F1/Precision/Recall Unknown)
| Issue | Impact | Solution |
|-------|--------|----------|
| **No CBP examination outcomes linked to shipments** | Can't validate: did high-risk shipments actually get seized? | Gather: Examination records from CBP APHIS/ports (6-12 month backlog) |
| **Mock risk_scores in fixtures** | Model trained on fabricated data | Create synthetic ground truth based on historical patterns OR partner with CBP for real outcomes |
| **No feedback loop from enforcement actions** | Model never learns from past mistakes | Implement post-examination model refinement (user marks "Correctly Flagged" / "False Positive") |

---

### 2. Missing Critical Feature Data

#### 2.1 Routing & AIS Data Gaps
| Feature | Current State | Required | Source |
|---------|---------------|----------|--------|
| **Real AIS dwell time** | Hardcoded typical_dwell (2-4 days) | Actual vessel tracking data with timestamp precision | MarineTraffic API / IHS Markit AIS |
| **Port call sequence anomalies** | Estimated route (origin → dest) | Complete waypoint history + deviation detection | Port authority APIs + AIS historical playback |
| **Vessel flag risk** | High-risk flags list (PA, KH, MH, MM) | Dynamic registry + ownership verification | IHS Fairplay / Equasis database |
| **Transshipment hub selection** | Known hubs list (SG, HK, LA, PA) | Confirmed transshipment patterns from cargo tracking | Altana / Panjiva supply chain data |

#### 2.2 Commodity & Pricing Gaps
| Feature | Current State | Required | Source |
|---------|---------------|----------|--------|
| **Benchmark prices** | Hardcoded $/kg by HS code (8541: $45) | Real-time market pricing with commodity futures | Bloomberg / ITC Trade Map / USITC |
| **Tariff rates** | Static rates (CN: 25%, VN: 150%) | Dynamic tariff exposure (Section 301 updates, AD/CVD reviews) | ITC / CBP tariff database (daily updates) |
| **HS code sensitivity** | Manual commodity sensitivity matrix | Real tariff rate + export control + forced labor list mapping | ECCN/CCL classification + UFLPA restricted list |
| **Cargo weight/density anomaly** | Not modeled | Volumetric weight vs declared weight comparison | Shipper manifest data + container capacity specs |

#### 2.3 Entity & Compliance Gaps
| Feature | Current State | Required | Source |
|---------|---------------|----------|--------|
| **OFAC/sanctions status** | Mocked in entity resolution | Real-time query + historical sanctions additions | OFAC SDN + Entity List + Watch List (daily syncs) |
| **Shipper age & establishment** | Score threshold (0-12mo: 9, 12-36mo: 6.5) | Actual business registration date + branch registration history | OpenCorporates / Local business registries |
| **Prior CBP violations** | Formula: violations_count × 2.5 | Actual violation records linked to shipper + type (ISF, tariff, CITES, etc.) | CBP ITDS + APHIS violation database |
| **Beneficial ownership opacity** | Shell company score (9/10) | Ownership chain verification via UBO registries | OpenOwnership / Transparency International + CORD |
| **Entity relationship network** | Not modeled | Hidden Chinese ownership in Canadian shippers? Multiple entities under same control? | Entity linking via common addresses/officers + Altana network analysis |

#### 2.4 Corridor-Specific Blind Spots

**CN→US (Export Control + Origin Concealment)**
- ❌ Missing: UFLPA forced labor detection (Xinjiang sourcing suppliers)
- ❌ Missing: Semiconductor supply chain mapping (CIPS wafer fab origins)
- ❌ Missing: Dual-use technology classification (EAR/ITAR items misclassified)
- ✓ Would need: Supplier facility mapping + raw material sourcing intelligence

**VN→US (Aluminum Tariff Evasion)**
- ❌ Missing: Aluminum alloy composition analysis (misclassification from pure aluminum)
- ❌ Missing: Transshipment via Hong Kong detection (VN→HK→US pattern)
- ❌ Missing: Related party pricing (transfer pricing strategies)
- ✓ Would need: Trade agreement rules of origin verification + chemical analysis of samples

**MY→US (Forced Labor + Solar)**
- ❌ Missing: Solar cell vs polysilicon supply chain (where in Malaysia was it actually made?)
- ❌ Missing: Semiconductor assembly facility verification (outsourced assembly locations)
- ❌ Missing: Labor audit records + certification verification
- ✓ Would need: Facility GPS verification + UFLPA certification database

**CA→US (Hidden Chinese Ownership)**
- ❌ Missing: Corporate structure depth (Canadian entity → Chinese parent → ultimate beneficial owner)
- ❌ Missing: Canadian rules of origin enforcement (USMCA preference verification)
- ❌ Missing: Transshipment detection (goods assembled in Canada from Chinese inputs)
- ✓ Would need: UBO registry + entity graph traversal + USMCA origin certification

---

### 3. Unknown Signal Interactions

| Signal Combination | Current Model | Missing Knowledge |
|--------------------|---------------|-------------------|
| **ISF_MISMATCH + DWELL_ANOMALY** | Both detected independently, +10% each | Are they correlated? Do they indicate coordinated concealment? |
| **New shipper + High-value commodity** | Party score 9/10 + Commodity 8/10 | Is the correlation multiplicative (9×8) or just additive? |
| **CN→US + Semiconductor** | Corridor 8.5 × Commodity 8.5 | Does export control complexity increase further (10/10)? |
| **UFLPA_RISK + Shipper_Age_New** | Both HIGH independently | Are new Malaysian suppliers MORE suspicious? Less? |
| **Price_Below_Market + High_Tariff_Rate** | Both trigger independently | Together = classic tariff evasion signal? Should boost score non-linearly? |

---

## DATA GATHERING & SYNTHETIC DATA STRATEGY

### Phase 1: Data Audit (Week 1-2)
```
1. Existing CBP Data Access
   - Request: 6-month examination records (Jan-Jun 2025) with outcomes
   - Structure: (shipment_id, exam_result: CLEARED/SEIZED/REFERRED, violation_type, penalty)
   - Expect: ~5,000-10,000 records from partner ports

2. Vendor Data Subscriptions
   - MarineTraffic (AIS): $5-10K/month for API access + historical archive
   - IHS Markit (vessel registry): $3-5K/month for sanctions + flagging data
   - ITC Trade Map: Free access (tariff rates + trade flows)
   - OpenCorporates: Free/paid tiers for entity establishment dates
```

### Phase 2: Synthetic Data Generation (Week 3-4)
**If real CBP data not available immediately:**

```python
# Synthetic shipment generator using realistic patterns

SYNTHETIC_DATA_STRATEGY = {
    'HIGH_RISK_PATTERNS': {
        'origin_concealment_cn': {
            'probability': 0.25,  # 25% of CN→US shipments are concealment attempts
            'characteristics': [
                'shipper_age < 12 months',
                'element9_mismatch = true',
                'route = CN → SG → US (transshipment)',
                'declared_value < market_price * 0.6',
                'new_importer = true'
            ],
            'expected_outcome': 'SEIZED'
        },
        'tariff_evasion_vn': {
            'probability': 0.20,
            'characteristics': [
                'commodity = aluminum_extrusions',
                'declared_price < benchmark_price * 0.7',
                'shipper_prior_violations >= 1',
                'port_dwell > 7 days',
                'manifest_completeness < 95%'
            ],
            'expected_outcome': 'EXAMINED'
        },
        'forced_labor_my': {
            'probability': 0.15,
            'characteristics': [
                'commodity_in_uflpa_list = true',
                'shipper_country = MY',
                'facility_audit_absent = true',
                'supply_chain_opacity_high = true'
            ],
            'expected_outcome': 'HELD_FOR_REVIEW'
        }
    },
    'LOW_RISK_PATTERNS': {
        'established_ca_exporter': {
            'probability': 0.70,
            'characteristics': [
                'shipper_age > 60 months',
                'prior_violations = 0',
                'element9_match = true',
                'usmca_cert_valid = true',
                'declared_price within 10% of benchmark'
            ],
            'expected_outcome': 'CLEARED'
        }
    },
    'SYNTHETIC_GENERATION_RULES': {
        'sample_size': 5000,  # Generate 5,000 synthetic shipments
        'distribution': {
            'HIGH_RISK': 0.30,  # 30% high-risk (realistic CBP prevalence)
            'MEDIUM_RISK': 0.50,  # 50% medium-risk
            'LOW_RISK': 0.20      # 20% low-risk
        },
        'correlation_injection': [
            'If element9_mismatch=true, increase price_variance by -15%',
            'If dwell_anomaly=true, increase route_deviation by 1.5x',
            'If shipper_new=true AND commodity_sensitive=true, boost risk by +15 points'
        ]
    }
}
```

---

## ALTANA INTEGRATION AS VALIDATION ORACLE

### Model Score → Altana Feedback Loop

```
WORKFLOW:
1. Model calculates initial risk_score (0-100)
   ↓
2. If risk_score >= 80: Query Altana API
   ├─ Supply chain visibility check (sanctioned suppliers in chain?)
   ├─ Beneficial ownership verification (is entity who it claims to be?)
   ├─ Trade finance red flags (payment anomalies?)
   ├─ Returned: altana_confidence (0-100%), altana_risk_factors
   ↓
3. Model Refinement Layer:
   ├─ If altana_confidence > 85% AND altana_agrees: Boost final_score +5 points
   ├─ If altana_confidence > 85% AND altana_disagrees: Reduce final_score -8 points
   ├─ If altana_confidence < 60%: Flag for manual review (inconclusive)
   ↓
4. Store refinement in audit_trail:
   {
     "model_initial_score": 82,
     "altana_query": true,
     "altana_response": {
       "confidence": 92,
       "risk_factors": ["sanctioned_supplier_detected", "high_transshipment_risk"],
       "recommendation": "HOLD_FOR_EXAMINATION"
     },
     "model_final_score": 87,
     "adjustment_reason": "Altana validated high supply chain risk"
   }
```

### AI Tuning Interface Integration

```typescript
// In AI Tuning page, new section: "Model Refinement Learning"

REFINEMENT_METRICS = {
  'altana_agreement_rate': 0.84,  // % of times Altana confirms our high-risk calls
  'altana_catch_rate': 0.12,      // % of times Altana flags things we missed
  'false_positive_rate': 0.08,    // % of time we flagged HIGH but exam was CLEAR
  'model_drift': 0.15,            // % cases where our score differs >15 points from Altana
  
  'suggested_factor_adjustments': [
    {
      'factor': 'PARTY_RISK',
      'current_weight': 0.15,
      'suggested_weight': 0.20,
      'reason': 'Altana data shows beneficial_ownership_opacity is 2.3x more predictive than current model'
    },
    {
      'factor': 'PATTERN_RISK',
      'current_weight': 0.10,
      'suggested_weight': 0.08,
      'reason': 'Price anomaly alone is less predictive; signals matter more. Recommend reduce weighting.'
    }
  ],
  
  'new_signals_to_add': [
    'sanctioned_supplier_in_chain',
    'entity_relationship_opacity_score',
    'trade_finance_anomaly'
  ]
}
```

---

## VALIDATION METRICS & SUCCESS CRITERIA

### Phase 0: Model Baseline (With Mock Data)
```
✓ Score distribution reasonable (not all 85+, not all <50)
✓ Signals correctly elevate component scores
✓ Corridor multipliers applied correctly
✓ Confidence interval calculation valid
→ **Success**: Model runs end-to-end without errors
```

### Phase 1: Synthetic Data Validation
```
✓ Model correctly identifies 80%+ of synthetic HIGH_RISK patterns
✓ Model score correlates with expected_outcome (HIGH_RISK → EXAMINED/SEIZED)
✓ Altana queries reduce model uncertainty (confidence_interval shrinks)
→ **Success**: Model ≥0.75 AUC on synthetic dataset
```

### Phase 2: Real CBP Data Validation (Post-Deployment)
```
✓ Precision: Of shipments we flag HIGH, % actually examined/seized
✓ Recall: Of shipments CBP actually examined, % we correctly scored HIGH
✓ F1 Score: Harmonic mean of precision/recall
✓ Calibration: Does score 85 really mean ~85% likelihood of exam?
→ **Success Target**: Precision ≥0.70, Recall ≥0.65, F1 ≥0.67
```

---

## RECOMMENDED IMMEDIATE ACTIONS

1. **This week**: Altana API integration (validation layer)
   - Add Altana client to `/api/altana_integration.py`
   - Create feedback loop: `score_shipment()` → if ≥80, call Altana
   - Store audit_trail in database

2. **This week**: AI Tuning page enhancement
   - Add "Model Refinement Metrics" section
   - Display: altana_agreement_rate, suggested_factor_adjustments, signals_to_add
   - Allow manual factor weight adjustment (preview impact on test cases)

3. **Next week**: Synthetic data generation
   - Build generator using rules above
   - Create 5K synthetic shipments with realistic patterns
   - Validate model achieves ≥0.75 AUC on synthetic data

4. **Ongoing**: Ground truth collection
   - Partnership with CBP for real examination outcomes
   - Historical backfill (6 months minimum)
   - Forward labeling (new shipments examined → outcomes logged)

---

## SUCCESS CRITERIA SUMMARY

| Metric | Current | Phase 1 Target | Production Target |
|--------|---------|----------------|-------------------|
| **Data Coverage** | 100% mock | 30% synthetic + validation | 80% real CBP outcomes |
| **Model Precision** | Unknown | 0.65 (synthetic) | 0.70+ (real data) |
| **Altana Agreement** | N/A | 75%+ | 85%+ |
| **Confidence Interval** | ±2.5 pts (static) | ±1.5 pts (Altana refined) | ±0.8 pts (feedback loops) |
| **Training Data Size** | 15 fixtures | 5,000 synthetic | 50,000+ real examinations |

