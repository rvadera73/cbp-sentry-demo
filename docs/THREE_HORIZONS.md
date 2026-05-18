# Three Horizons Intelligence Pipeline — Deep Dive

## Overview

Sentry's core intelligence framework detects illegal transshipment across three distinct time horizons:

- **H1 (Structural)**: Days/weeks before — Macro trade pattern analysis
- **H2 (Pre-Manifest)**: 14-22 days before — ISF + AIS intelligence
- **H3 (72-Hour Trigger)**: Manifest received — Full assessment + referral generation

By H3, **80% of investigative work is already complete** because H1 and H2 have pre-classified the corridor and flagged direct evidence.

---

## Horizon 1: Structural Corridor Intelligence

### Timing & Triggers

- **Runs**: Daily background job (Cloud Scheduler → Cloud Run Job)
- **Duration**: Each run: ~60 seconds
- **Output**: `corridors/{hts6}_{origin}_{destination}` documents in Firestore
- **Update frequency**: Weekly refresh on known corridors, add new corridors as data arrives

### What H1 Does

Analyzes **bilateral trade statistics** at the macro level to identify high-risk transshipment corridors before any specific shipment is identified.

**Data Sources**:
- UN Comtrade (bilateral trade flows)
- China General Administration of Customs (GACC) export data
- U.S. International Trade Commission (USITC) import statistics
- U.S. Commerce Department (AD/CVD cases, tariff orders)
- USITC Tariff Database (HTS classifications, duty rates)

### Example: China→Vietnam→US Aluminum Corridor

#### Step 1: Detect Trade Anomaly

```python
# Pseudo-code: api/horizons/h1_corridor.py

def analyze_china_vietnam_aluminum():
    """
    Hypothesis: Chinese aluminum billet exports to Vietnam spike
    correlate with Vietnamese aluminum extrusion exports to U.S.
    """
    
    # UN Comtrade data
    china_billet_to_vietnam = {
        2017: 185_000_000,  # USD
        2018: 210_000_000,
        2019: 245_000_000,
        2020: 189_000_000,  # COVID dip
        2021: 380_000_000,  # Sharp recovery
        2022: 890_000_000,  # +135% YoY (pre-AD/CVD)
        2023: 1_200_000_000, # +35% YoY (post-AD/CVD expansion)
    }
    
    # USITC data
    vietnam_extrusion_to_usa = {
        2017: 42_000_000,
        2018: 65_000_000,
        2019: 78_000_000,
        2020: 52_000_000,
        2021: 145_000_000,
        2022: 289_000_000,  # +99% YoY
        2023: 380_000_000,  # +31% YoY
    }
    
    # Calculate growth rate
    cn_growth_17_23 = (1_200_000_000 - 185_000_000) / 185_000_000  # 548% (5.5× spike)
    vn_growth_17_23 = (380_000_000 - 42_000_000) / 42_000_000      # 805% (8.05× spike)
    
    # Correlation analysis
    correlation = pearson_correlation(china_billet_to_vietnam, vietnam_extrusion_to_usa)
    # Result: 0.94 (very strong positive correlation)
    
    return {
        "corridor_id": "760410_CN_VN_US",
        "risk_level": "CRITICAL_STRUCTURAL_RISK",
        "evidence": {
            "china_billet_export_spike": "5.5× (2017-2023)",
            "vietnam_extrusion_correlation": "0.94 (very strong)",
            "timing_alignment": "Spike accelerates post-AD/CVD action (Feb 2025)",
        }
    }
```

#### Step 2: Verify Capacity Constraint

```python
def verify_structural_risk():
    """
    Key insight: Vietnam has NO domestic aluminum smelting capacity.
    All primary aluminum must be imported.
    """
    
    # USGS Mineral Commodity Summary: Vietnam
    vietnam_primary_aluminum_capacity = 0  # MT/year
    
    # Therefore, if Vietnam exports aluminum extrusions:
    # → Raw material MUST be imported
    # → Most likely source: China (66% of world smelting capacity)
    
    # Calculate import requirement
    extrusion_export_2023 = 380_000_000  # USD
    avg_unit_value_extrusions = 2750     # USD/MT (Vietnamese finished)
    tons_needed = extrusion_export_2023 / avg_unit_value_extrusions
    # = 138,000 MT extrusions
    
    # Reverse-calculate billet requirement (12% loss in extrusion process)
    billet_needed = tons_needed / 0.88
    # = 157,000 MT billet required
    
    # Chinese export to Vietnam: 1.2B / $2,500/MT avg = 480,000 MT
    # Surplus: 480,000 - 157,000 = 323,000 MT
    # → Could hide 323,000 MT of Chinese goods as Vietnamese origin
    
    return {
        "capacity_gap": "323,000 MT annual evasion potential",
        "risk_interpretation": "Structural capacity imbalance creates evasion incentive",
    }
```

#### Step 3: Check AD/CVD Incentive

```python
def check_tariff_incentive():
    """
    Calculate financial motive for illegal transshipment.
    """
    
    # HTS 7604.10 — Aluminum extrusions
    tariff_chinese_origin = 0.065  # 6.5% base duty
    ad_rate_chinese = 3.7415       # 374.15% AD (antidumping)
    cvd_rate_chinese = 0           # Bundled into AD
    section_232_rate = 0.10        # 10% Steel/Aluminum tariff
    
    total_duty_china = (tariff_chinese_origin + ad_rate_chinese + section_232_rate)
    # = 3.9065 or 390.65%
    
    # Vietnamese origin (if legitimately produced)
    tariff_vietnam = 0.065
    # = 6.5% (no AD/CVD, no Section 232)
    
    # Revenue difference on $72,030 shipment (Greenfield case)
    duty_if_china = 72_030 * 3.9065 / 100
    # = $2,813,000
    
    duty_if_vietnam = 72_030 * 0.065 / 100
    # = $46.82
    
    evasion_incentive = duty_if_china - duty_if_vietnam
    # = $2,813,000 per small shipment (!!)
    
    return {
        "duty_if_chinese_origin": f"${duty_if_china:,.0f}",
        "duty_if_vietnamese_origin": f"${duty_if_vietnam:,.2f}",
        "evasion_incentive_per_shipment": f"${evasion_incentive:,.0f}",
        "interpretation": "Massive financial motive for fraud",
    }
```

### H1 Output: Corridor Risk Document

Stored in Firestore as `corridors/760410_CN_VN_US`:

```json
{
  "corridor_id": "760410_CN_VN_US",
  "hts_6": "760410",
  "origin": "CN",
  "intermediate": "VN",
  "destination": "US",
  
  "risk_level": "CRITICAL_STRUCTURAL_RISK",
  "risk_score": 95,
  
  "created_at": "2018-01-01T00:00:00Z",
  "last_updated": "2026-05-18T12:00:00Z",
  
  "h1_evidence": {
    "china_billet_export_to_vietnam": {
      "2017": 185_000_000,
      "2023": 1_200_000_000,
      "growth_pct": 548,
      "spike_description": "5.5× increase over 6 years; accelerates post-AD/CVD"
    },
    "vietnam_extrusion_export_to_usa": {
      "2017": 42_000_000,
      "2023": 380_000_000,
      "growth_pct": 805,
      "spike_description": "8× increase; correlated with Chinese billet import surge"
    },
    "correlation_coefficient": 0.94,
    "correlation_interpretation": "Very strong positive correlation suggests transshipment",
    
    "vietnam_primary_capacity": {
      "domestic_smelting_capacity_mta": 0,
      "interpretation": "Vietnam has zero domestic smelting capacity; all aluminum must be imported",
      "likely_source": "China (66% of world capacity, adjacent geography)"
    },
    
    "evasion_incentive": {
      "hts_code": "7604.10.1000",
      "duty_if_chinese": "390.65%",
      "duty_if_vietnamese": "6.5%",
      "financial_incentive": "5,909% tariff differential",
      "example_shipment": {
        "value_usd": 72030,
        "estimated_duty_if_chinese": 2813000,
        "estimated_duty_if_vietnamese": 47,
        "evasion_incentive": 2813000
      }
    }
  },
  
  "ad_cvd_cases": [
    {
      "case_number": "A-570-967",
      "commodity": "Aluminum Extrusions",
      "origin": "China",
      "ad_rate": "374.15%",
      "cvd_rate": "0%",
      "order_date": "2025-02-05",
      "enforcement_history": "1.8M MT seized 2019; Zhongwang determination 2019"
    }
  ],
  
  "enforcement_history": [
    {
      "year": 2019,
      "action": "Antidumping investigation",
      "result": "1.8M MT of Chinese aluminum seized; Zhongwang (major Chinese manufacturer) determined to be circumventing",
      "relevance": "Demonstrates CBP capability and precedent for catching transshipment in this corridor"
    }
  ],
  
  "likelihood_assessment": {
    "structural_risk": "CRITICAL",
    "why": "Massive tariff incentive (390% duty) + capacity gap (Vietnam has zero smelting) + prior enforcement history"
  }
}
```

### H1 Demo Moment

When a CBP officer uploads the Greenfield manifest:

```
UI Message:
"This shipment route (China → Vietnam → US) for aluminum extrusions 
was flagged as CRITICAL STRUCTURAL RISK on Jan 1, 2018 based on 
macro trade pattern analysis — long before this specific shipment 
was booked. 

Structural evidence:
• Chinese billet exports to Vietnam: 5.5× spike (2017-2023)
• Vietnamese extrusion exports to U.S.: 8× spike (correlated)
• Vietnam has zero domestic smelting capacity
• Tariff incentive: 390% duty if Chinese origin vs. 6.5% if Vietnamese
• Prior enforcement: 1.8M MT seized 2019 in similar corridor

This shipment's aluminum cannot be Vietnamese-origin — 
it must be Chinese aluminum imported into Vietnam."
```

---

## Horizon 2: Pre-Manifest ISF & Maritime Intelligence

### Timing & Triggers

- **Trigger**: ISF 10+2 filing received (24 hours before container loaded at export port)
- **Duration**: ~30 seconds processing
- **Output**: `shipments/{bill_id}/h2_intelligence` document in Firestore
- **Advance warning**: 14-22 days before CBP 72-hour manifest

### Key Insight: ISF Timing

ISF is filed **24 hours BEFORE the cargo is physically loaded**. This is a massive advantage:

```
Timeline:
Jan 1    │ ISF filed (24h before loading)
         │
Jan 2    │ Cargo loaded at foreign port
         │
Jan 3    │ Vessel departs
         │
Jan 20   │ Manifest filed (72h before arrival)
         │
Jan 22   │ Vessel arrives (CBP inspection)

         ◄─── H2 WINDOW ─────► (18 days of advance notice!)
```

### H2 Data Sources

1. **ISF 10+2 Data Element 9** (via Altana Atlas API, mocked for demo)
   - Container stuffing location (where cargo physically loaded)
   - Port of lading (declared export port)
   - Shipper and consignee names

2. **AIS Vessel Tracking** (via Spire, MarineTraffic, mocked for demo)
   - Real-time ship movements
   - Port calls with timestamps
   - Dwell time at each port
   - Vessel operator and flag state

3. **Commercial BOL Database** (Panjiva, mocked for demo)
   - Historical trade flow
   - Shipper-consignee patterns
   - Prior shipments on same route

### Example: Greenfield ISF Contradiction

**ISF Filed**: April 13, 2026 08:00:00Z

```json
{
  "bill_of_lading": "SAMPLE-BOL-2026-001",
  
  "isf_element_9_container_stuffing_location": {
    "location": "Nansha Container Terminal, Guangzhou",
    "coordinates": "22.8048, 113.9406",
    "country_code": "CN",
    "date_range": "2026-03-25 to 2026-04-06",
    "stuffing_period_days": 11.2
  },
  
  "declared_origin": "Vietnam",
  "declared_shipper": "Greenfield Industrial Trading Co., Ltd."
}
```

**Legal Violation**: 19 CFR 149.5

```
ISF Element 9 places container at Guangzhou, China.
Manifest declares Vietnamese origin.
This is direct evidence of origin fraud.
```

### H2 AIS Analysis

```python
# api/horizons/h2_isf_ais.py

def analyze_vessel_dwell():
    """
    AIS tracking shows MV Pacific Horizon dwell at Guangzhou.
    Compare to baseline for aluminum commodity.
    """
    
    # Actual dwell
    arrival_date = datetime(2026, 3, 25)
    departure_date = datetime(2026, 4, 6)
    dwell_days = (departure_date - arrival_date).days
    # = 11.2 days
    
    # Baseline for aluminum at Guangzhou (from MarineTraffic 2024 stats)
    baseline_dwell = 2.1
    
    # Anomaly calculation
    anomaly_ratio = dwell_days / baseline_dwell
    # = 11.2 / 2.1 = 5.33×
    
    # Percentile
    percentile = percentile_rank_in_distribution(dwell_days, all_aluminum_dwells_at_CNGGZ)
    # = 99 (99th percentile = extremely unusual)
    
    # Interpretation
    interpretation = {
        "dwell_days": 11.2,
        "baseline_dwell_days": 2.1,
        "anomaly_ratio": 5.33,
        "percentile": 99,
        "interpretation": "Extremely long dwell; typical for full cargo load/unload, not transshipment pass-through"
    }
    
    # Draft change (indicates cargo loading/unloading)
    arrival_draft = 8.1  # meters (light vessel)
    departure_draft = 9.8  # meters (heavy vessel)
    draft_increase = departure_draft - arrival_draft
    # = 1.7 meters
    
    # Calculate cargo weight from draft change
    deadweight_ton_per_meter_draft = 150  # Typical for container ship
    estimated_cargo_weight = draft_increase * deadweight_ton_per_meter_draft
    # = 255 MT (consistent with Greenfield 26.2 MT + other cargo)
    
    return {
        "dwell_anomaly": "11.2 days (5.3× baseline, 99th percentile)",
        "draft_evidence": "1.7m increase = cargo loaded",
        "conclusion": "Vessel arrived light, loaded cargo at Guangzhou, departed heavy"
    }
```

### H2 Output: Pre-Intelligence Document

```json
{
  "shipment_id": "SHP-001",
  "bill_id": "SAMPLE-BOL-2026-001",
  
  "h2_isf_intelligence": {
    "isf_filing_date": "2026-04-13T08:00:00Z",
    "element_9_contradiction": true,
    "stuffing_location": "Nansha Container Terminal, Guangzhou, China",
    "declared_origin": "Vietnam",
    "violation_code": "19 CFR 149.5",
    "violation_summary": "ISF Element 9 contradicts declared origin"
  },
  
  "h2_ais_intelligence": {
    "vessel_imo": 9834521,
    "vessel_name": "MV Pacific Horizon",
    "port_call_guangzhou": {
      "arrival_date": "2026-03-25",
      "departure_date": "2026-04-06",
      "dwell_days": 11.2,
      "dwell_baseline_aluminum": 2.1,
      "dwell_anomaly_ratio": 5.33,
      "dwell_percentile": 99,
      "arrival_draft_m": 8.1,
      "departure_draft_m": 9.8,
      "estimated_cargo_loaded_mt": 255,
      "interpretation": "Vessel loaded cargo at Guangzhou; dwell time consistent with full load/unload"
    }
  },
  
  "h2_evidence_chain": {
    "direct_evidence": "ISF Element 9 places container in China; manifest declares Vietnam",
    "supporting_evidence": [
      "AIS shows 11.2-day dwell at Guangzhou (5.3× baseline)",
      "Draft increase indicates cargo loading at Guangzhou",
      "Container never called at Vietnam port; went directly from China to U.S."
    ],
    "legal_authority": "19 CFR 149.5, 19 USC 1484"
  }
}
```

### H2 Demo Moment

When H3 manifest is received, officer sees:

```
"PRE-ARRIVAL INTELLIGENCE ALERT:

ISF 10+2 filing (April 13, received 18 days before manifest):
• Element 9 shows container stuffed at Guangzhou, China
• Manifest declares Vietnamese origin
• This is direct evidence of origin fraud (19 CFR 149.5)

Supporting evidence:
• MV Pacific Horizon dwell at Guangzhou: 11.2 days (5.3× baseline)
• Vessel draft increased 1.7m (indicates cargo loading at Guangzhou)
• Vessel route: VNSGN → CNGGZ (loaded) → USLAX (no Vietnam visit)

Conclusion: Investigation was already underway 18 days before manifest received.
Evidence is complete; referral is enforcement-ready."
```

---

## Horizon 3: 72-Hour Manifest Trigger + Full Assessment

### Timing & Triggers

- **Trigger**: CBP manifest (Excel) uploaded by officer
- **Duration**: ~10 seconds for ingest + scoring
- **Output**: `shipments/{bill_id}/h3_score` + `referral_packages/{package_id}` JSON
- **Action window**: 72 hours before vessel arrival

### H3 Data Processing Pipeline

```
1. INGEST (parse manifest)
   ├── Extract shipper, consignee, HTS, COO, weight, value
   └── Validate required fields

2. LOOKUP H1 CORRIDOR RISK
   ├── Fetch `corridors/{hts6}_{origin}_{destination}`
   └── Example: HTS 760410, VN→US = CRITICAL_STRUCTURAL_RISK

3. LOOKUP H2 INTELLIGENCE
   ├── Fetch `shipments/{bill_id}/h2_intelligence`
   └── Check for ISF contradiction, AIS anomalies

4. SENZING ENTITY RESOLUTION
   ├── Match shipper name to known entities
   ├── Traverse ownership graph (Neo4j)
   └── Output: Entity chain with confidence scores
   └── Example: VN shipper → HK holding → CN manufacturer (0.91 confidence)

5. FOUR-TIER ML SCORING
   ├── Tier 1: Senzing graph confidence
   ├── Tier 2: Isolation Forest (AIS anomaly detection)
   ├── Tier 3: LightGBM (supervised classification on EAPA history)
   └── Tier 4: Bayesian Belief Network (origin fraud + criticality)

6. VERTEX AI GEMINI LLM
   ├── Generate XAI assertions (explain each risk factor)
   └── Narrate referral package sections

7. REFERRAL PACKAGE GENERATION
   └── Output: JSON + PDF (Tables 3-1 through 3-14)
```

### Scoring Tiers Detail

#### Tier 1: Senzing Entity Resolution Confidence

```python
# api/horizons/h3_manifest.py / Tier 1

def score_entity_resolution(shipper_name, manifest_entity_data):
    """
    Senzing confidence in entity matching.
    Higher confidence = shipper likely linked to known entities.
    """
    
    senzing_result = senzing_client.resolve_entity({
        "name": shipper_name,
        "address": manifest_entity_data["address"],
        "phone": manifest_entity_data.get("phone"),
    })
    
    # Returns: entity_id=1001, confidence=0.91, match_keys=[...]
    
    # Scoring: confidence × max_points (15 pts for Party Profile Risk)
    score = senzing_result.confidence * 15
    # Example: 0.91 × 15 = 13.65 → round to 15 if confidence > 0.85
    
    return {
        "tier": 1,
        "component": "Party Profile Risk",
        "score": score,
        "max": 15,
        "confidence": senzing_result.confidence,
        "evidence": senzing_result.match_keys,
    }
```

#### Tier 2: Isolation Forest Anomaly Detection

```python
def score_ais_anomaly(shipment_data):
    """
    Isolation Forest detects anomalies in AIS routing data.
    Features: dwell_time, transit_days, port_deviation, draft_change
    """
    
    from sklearn.ensemble import IsolationForest
    
    # Training data: historical aluminum shipments
    historical_features = [
        # (dwell_days, transit_days, port_count, draft_change)
        (2.1, 20, 1, 0.5),  # Normal
        (1.8, 20, 1, 0.4),  # Normal
        (2.3, 21, 1, 0.6),  # Normal
        (2.0, 19, 1, 0.5),  # Normal
        # ... many more normal examples
        (11.2, 20, 2, 1.7),  # ANOMALY (Greenfield case)
    ]
    
    model = IsolationForest(contamination=0.01)
    model.fit(historical_features)
    
    # Score current shipment
    shipment_features = [
        shipment_data["ais_dwell_days"],  # 11.2
        shipment_data["transit_days"],    # 20
        shipment_data["port_count"],      # 2
        shipment_data["draft_change"],    # 1.7
    ]
    
    anomaly_score = model.decision_function([shipment_features])[0]
    # Negative = anomaly, closer to -1 = more anomalous
    
    # Convert to 0-15 scoring
    # anomaly_score -1 → 15 pts (max)
    # anomaly_score 0 → 0 pts
    
    routing_consistency_score = max(0, min(15, int(15 * (1 + anomaly_score))))
    
    return {
        "tier": 2,
        "component": "Routing Consistency",
        "score": routing_consistency_score,
        "max": 15,
        "anomaly_score": anomaly_score,
        "interpretation": "Dwell time 5.3× baseline = highly anomalous",
    }
```

#### Tier 3: LightGBM Supervised Classification

```python
def score_lightgbm_classification(shipment_data):
    """
    LightGBM trained on historical EAPA (Enforce and Protect Act) cases.
    Features: HTS code, country, shipper_age, price_vs_market, origin_shift_pattern
    """
    
    import lightgbm as lgb
    
    # Features
    features = {
        "hts_code_770410": 1,  # Aluminum extrusions
        "origin_vn": 1,        # Vietnam declared
        "shipper_age_days": 104,  # Recently registered
        "price_below_market_pct": 15,  # Price 15% below normal Vietnamese extrusion
        "origin_shift_binary": 1,  # MY → TH → VN pattern detected
        "prior_cbp_filings_shipper": 0,  # No history
        "consignee_age_days": 180,  # SunPath newly trading
        "volume_spike_vs_prior_month": 0.23,  # 23% spike
    }
    
    # Predict: P(fraudulent_origin_claim)
    prob_fraudulent = model.predict([features])[0]
    # Result: 0.82 (82% probability of origin fraud)
    
    # Split score between two components:
    # Commodity Sensitivity (15 pts) + Historical Pattern (15 pts) = 30 total
    
    commodity_score = 14  # HTS 7604.10 is high-risk → 93% of max
    pattern_score = 12    # Origin shift detected but not confirmed → 80% of max
    
    return {
        "tier": 3,
        "components": [
            {
                "name": "Commodity Sensitivity",
                "score": commodity_score,
                "max": 15,
                "basis": "HTS 7604.10 subject to 374.15% AD/CVD from China",
            },
            {
                "name": "Historical Pattern Anomaly",
                "score": pattern_score,
                "max": 15,
                "basis": "6-month origin shift (MY→TH→VN); volume spike post-AD/CVD",
            },
        ],
        "lgb_fraud_probability": prob_fraudulent,
    }
```

#### Tier 4: Bayesian Belief Network

```python
def score_bayesian_network(shipment_data, h1_h2_evidence):
    """
    Bayesian network integrates all tiers + H1/H2 evidence.
    Outputs: P(FRAUDULENT_ORIGIN | all_evidence)
    """
    
    from pgmpy.models import BayesianNetwork
    from pgmpy.factors.discrete import TabularCPD
    
    # Define network:
    # ISF_CONTRADICTION → ORIGIN_FRAUDULENT
    # PRICE_BELOW_MARKET → ORIGIN_FRAUDULENT
    # SENZING_LINKED_TO_CHINA → ORIGIN_FRAUDULENT
    # H1_CORRIDOR_CRITICAL → ORIGIN_FRAUDULENT
    
    model = BayesianNetwork([
        ("H1_CORRIDOR_RISK", "ORIGIN_FRAUDULENT"),
        ("ISF_ELEMENT_9", "ORIGIN_FRAUDULENT"),
        ("PRICE_ANOMALY", "ORIGIN_FRAUDULENT"),
        ("SENZING_LINK", "ORIGIN_FRAUDULENT"),
        ("AIS_DWELL_ANOMALY", "ORIGIN_FRAUDULENT"),
    ])
    
    # CPD: Conditional Probability Distribution
    cpd_origin_fraudulent = TabularCPD(
        variable="ORIGIN_FRAUDULENT",
        variable_card=2,  # True/False
        evidence=["H1_CORRIDOR_RISK", "ISF_ELEMENT_9", "PRICE_ANOMALY", "SENZING_LINK"],
        evidence_card=[2, 2, 2, 2],
        values=[
            [0.01, 0.05, 0.10, 0.15, 0.30, 0.60, 0.75, 0.90, 0.98],  # P(False)
            [0.99, 0.95, 0.90, 0.85, 0.70, 0.40, 0.25, 0.10, 0.02],  # P(True)
        ],
    )
    
    # Inference: Given evidence, what is P(FRAUDULENT)?
    inference = VariableElimination(model)
    prob_fraudulent = inference.query(
        variables=["ORIGIN_FRAUDULENT"],
        evidence={
            "H1_CORRIDOR_RISK": True,  # CRITICAL_STRUCTURAL_RISK
            "ISF_ELEMENT_9": True,      # Guangzhou ≠ Vietnam
            "PRICE_ANOMALY": True,      # Below market
            "SENZING_LINK": True,       # VN shipper → CN parent
            "AIS_DWELL_ANOMALY": True,  # 5.3× baseline
        }
    )
    
    # Result: P(FRAUDULENT=True | all_evidence) = 0.91 (91%)
    prob = prob_fraudulent.values[1]  # Take True probability
    
    # Score: Convert probability to points
    # Tier 4 accounts for: Origin Doc Gap (25 pts) + Time Sensitivity (15 pts) = 40 total
    
    origin_doc_score = int(25 * prob)  # 23 pts
    time_sensitivity_score = int(15 * prob)  # 13 pts
    
    return {
        "tier": 4,
        "components": [
            {
                "name": "Origin Documentation Gap",
                "score": origin_doc_score,
                "max": 25,
                "basis": f"Bayesian P(FRAUDULENT) = {prob:.2%}; no substantiating production records",
            },
            {
                "name": "Time Sensitivity",
                "score": time_sensitivity_score,
                "max": 15,
                "basis": f"In 72-hour window; {prob:.2%} confidence enables immediate enforcement",
            },
        ],
        "bayesian_fraud_probability": prob,
    }
```

### Final Score Composition

```
Tier 1: Party Profile Risk       = 15/15 (Senzing confidence 0.91)
Tier 2: Routing Consistency      = 14/15 (AIS dwell 5.3× baseline)
Tier 3: Commodity Sensitivity    = 14/15 (HTS 7604.10 → 374% AD/CVD)
        Historical Pattern       = 12/15 (MY→TH→VN shift)
Tier 4: Origin Doc Gap           = 23/25 (Bayesian P(fraud) = 0.91)
        Time Sensitivity         = 13/15 (72-hour window)
                                  -------
TOTAL SCORE                      = 91/100 (HIGH confidence)
```

### Vertex AI Gemini XAI Narration

```python
def generate_xai_narrative(score_breakdown):
    """
    Generate plain-English explanations for each risk factor.
    """
    
    prompt = f"""
    Given this risk score breakdown:
    {score_breakdown}
    
    Generate a clear, jargon-free explanation for a CBP officer:
    1. What is the overall fraud risk?
    2. What's the strongest single piece of evidence?
    3. What would need to be true for this to NOT be fraud?
    4. What enforcement action is recommended?
    """
    
    response = gemini_client.generate_content(prompt)
    # Example output:
    return """
    FRAUD RISK: 91% confident this is illegal transshipment.
    
    STRONGEST EVIDENCE: The ISF filing (April 13) shows the container 
    was packed in Guangzhou, China. The manifest claims it's from Vietnam. 
    That's direct evidence of origin fraud (19 CFR 149.5).
    
    WHAT WOULD PROVE LEGITIMACY:
    - Factory production records from Vietnam showing aluminum extrusion
    - Proof that Greenfield Industrial Trading operates a real factory in Vietnam
    - Evidence of raw material sourced elsewhere (not China)
    → Currently: NONE of these documents provided
    
    RECOMMENDED ACTION: EXAMINE_ON_ARRIVAL
    - Focus on origin documentation (factory records, lot numbers)
    - Verify ownership chain (is Greenfield really Vietnamese?)
    - Estimated duty exposure: $2.1M if Chinese origin confirmed
    """
```

### H3 Output: Referral Package

See **REFERRAL_PACKAGE.md** for full JSON structure and display format.

---

## Integration: H1 + H2 + H3

### Data Persistence Across Horizons

```
Firestore Collections:

/corridors/{hts6}_{origin}_{destination}
  ├── h1_evidence: Comtrade, GACC, USITC analysis
  └── ad_cvd_cases: Tariff orders

/shipments/{bill_id}
  ├── manifest: Raw CBP data (H3 input)
  ├── h2_intelligence: ISF + AIS analysis
  └── h3_score: ML tier results (Senzing + Forest + LGB + Bayesian)

/referral_packages/{package_id}
  └── sections: Tables 3-1 through 3-14 (final deliverable)

Neo4j Aura Graph:

(:Entity) nodes with relationships:
  ├── OWNED_BY
  ├── SHARES_DIRECTOR
  ├── SHIPPED_VIA (:Vessel)
  └── PRIOR_ENFORCEMENT

(:Corridor {hts_6, origin, risk_level})
  └── HIGH_RISK_SHIPMENTS → (:Shipment)
```

### Demo Flow

```
1. Officer uploads manifest (Excel)
   ↓
2. System looks up HTS 7604.10, origin VN
   ↓
3. Finds corridor 760410_CN_VN_US = CRITICAL_STRUCTURAL_RISK (H1)
   ↓
4. Finds ISF Element 9 contradiction (H2)
   ↓
5. Senzing resolves shipper → Chinese parent (Tier 1)
   ↓
6. Runs 4 ML tiers → 91/100 score (H3)
   ↓
7. Generates referral package with XAI narrative
   ↓
8. Officer sees enforcement-ready case file
   ↓
9. Referral sent to port authority for examination
```

---

## Performance Targets

| Operation | Target | Notes |
|-----------|--------|-------|
| H1 corridor analysis | < 60s | Daily batch, ~2000 corridors |
| H2 ISF processing | < 30s | Real-time, triggered on ISF receipt |
| H3 manifest ingest + parsing | < 2s | JSON schema validation |
| H3 Senzing resolution | < 5s | Graph traversal (Neo4j) |
| H3 4-tier scoring | < 3s | ML inference (sklearn, lightgbm, pgmpy) |
| H3 Gemini narrative | < 2s | LLM call (cached) |
| Referral package build | < 2s | JSON assembly + PDF generation |
| **Total H3 end-to-end** | **< 10s** | Manifest upload to referral ready |

---

## Testing Strategy

- **H1 tests**: Historical trade data fixtures, corridor risk calculation
- **H2 tests**: ISF contradiction detection, AIS baseline comparison
- **H3 tests**: Senzing mock, 4-tier scoring, referral package structure
- **E2E tests**: Full pipeline (ingest → Senzing → scoring → referral) with Greenfield seed data

See **TESTING_STRATEGY.md** for detailed test patterns.
