# Data Seeding Strategy: Risk Score Models

## PROBLEM

Currently, `risk_score` is pre-stored in the shipments table with static values (e.g., 97.0).
This causes discrepancies with the dynamic comprehensive risk scoring calculation.

## SOLUTION

Make risk scoring **fully dynamic**:
1. Remove or deprecate pre-stored risk_score
2. Calculate via `/api/risk-scoring/comprehensive` endpoint on-demand
3. Seed shipments with **characteristics** (not pre-computed scores)
4. Let the risk scoring model compute based on components

---

## COMPONENT-BASED RISK FACTORS

Risk is calculated from 17 components across 7 factors:

### **High-Risk Profiles (95%+ Score)**
Should combine multiple high-risk components:

#### Profile 1: Origin Concealment
- **Documentation Risk**: ISF Element 9 mismatch (declared ≠ actual)
- **Corridor Risk**: China→US (baseline 1.30x multiplier)
- **Commodity Risk**: HS code with AD/CVD (25% tariff rate)
- **Routing Risk**: High dwell time (>7 days), transshipment via Hong Kong
- **Party Risk**: Shipper age < 6 months, shipper_country ≠ declared_origin
- **Pattern Risk**: Price variance >30% below benchmark
- **Time Sensitivity**: Pre-tariff announcement timing

**Expected Score**: 90-99%

```sql
INSERT INTO shipments (
  shipper_name, origin_country, destination_country, 
  hs_code, declared_value_usd, element9_is_mismatch, 
  element9_declared_country, element9_actual_country,
  shipper_age_months, dwell_days, ad_cvd_applicable, ad_cvd_rate,
  port_calls, vessel_flag, status, created_at
) VALUES
(
  'Shanghai Trade Co.', 'CN', 'US', '6204.29', 185000, 1,
  'VN', 'CN',  -- Element 9 mismatch
  3,           -- Shipper age < 6 months
  9,           -- Dwell > 5x baseline
  1, 0.25,     -- AD/CVD 25%
  'HK,SG,LA',  -- Transshipment route
  'HK',        -- Flag of convenience
  'FILED', CURRENT_TIMESTAMP
);
```

#### Profile 2: Circular Invoicing Ring
- **Party Risk**: Multiple related entities (beneficial owner shell)
- **Pattern Risk**: High volume, low value (revenue under-invoicing)
- **Routing Risk**: Repeated route (same shipper → same consignee, 10+ times/year)
- **Commodity Risk**: Restricted technology (HS 9011 - optical instruments for lithography)
- **Documentation Risk**: Minimal supporting docs (no bill of materials)
- **Corridor Risk**: UAE/HK re-export to US

**Expected Score**: 92-98%

```sql
INSERT INTO shipments VALUES (
  'Emirates Tech Trading LLC', 'AE', 'US', '9011.90.30', 45000, 0,
  'AE', 'AE',
  8, 2, 0, 0,
  'AE,HK,LA', 'LB', 'FILED', CURRENT_TIMESTAMP
);
```

#### Profile 3: UFLPA/Sanctions Red Flag
- **Party Risk**: OFAC match = TRUE
- **Commodity Risk**: UFLPA-controlled goods (cotton, solar, tomatoes)
- **Corridor Risk**: High-risk country (OFAC-sanctioned entity)
- **Time Sensitivity**: Recent enforcement action on shipper

**Expected Score**: 94-99%

```sql
INSERT INTO shipments VALUES (
  'Xinjiang Cotton Mills', 'CN', 'US', '5208.11', 280000, 0,
  'CN', 'CN',
  24, 1, 0, 0,
  'CN,LA', 'CN', 'FILED', CURRENT_TIMESTAMP
) 
-- Must add OFAC_MATCH = 1 in a separate update
```

---

### **Medium-Risk Profiles (60-70% Score)**

#### Profile 4: Shipper Age Red Flag
- **Party Risk**: New shipper (0-3 months old)
- **Documentation Risk**: Standard docs only (no factory records)
- **Corridor Risk**: Baseline corridor (CA/MX)
- **Pattern Risk**: First-time shipper, reasonable quantities
- **Routing Risk**: Direct route, standard ports

**Expected Score**: 62-68%

```sql
INSERT INTO shipments VALUES (
  'New Trading LLC', 'CA', 'US', '8471.30', 95000, 0,
  'CA', 'CA',
  1,           -- 1 month old
  2, 0, 0,
  'CA,LA', 'CA', 'FILED', CURRENT_TIMESTAMP
);
```

#### Profile 5: Transshipment Dwell Anomaly
- **Routing Risk**: Unusual dwell at transshipment hub (6-8 days, baseline 2 days)
- **Pattern Risk**: One-time transshipment (not regular practice)
- **Commodity Risk**: Moderate tariff exposure
- **Party Risk**: Established shipper (>12 months)
- **Documentation Risk**: Complete ISF, Element 9 matches

**Expected Score**: 64-70%

```sql
INSERT INTO shipments VALUES (
  'Singapore Trade Partners', 'MY', 'US', '3926.30', 125000, 0,
  'MY', 'MY',
  36, 7,  -- 7 days dwell (vs 2-day baseline)
  1, 0.05,
  'MY,SG,LA', 'SG', 'FILED', CURRENT_TIMESTAMP
);
```

#### Profile 6: AD/CVD Corridor Risk
- **Commodity Risk**: HS code under active AD/CVD orders (12% rate)
- **Corridor Risk**: Vietnam/China with high tariff incentive
- **Party Risk**: Established shipper
- **Routing Risk**: Standard routing
- **Documentation Risk**: All docs provided

**Expected Score**: 65-72%

```sql
INSERT INTO shipments VALUES (
  'Vietnam Aluminum LLC', 'VN', 'US', '7610.10', 156000, 0,
  'VN', 'VN',
  48, 3,
  1, 0.12,  -- AD/CVD 12%
  'VN,SG,LA', 'VN', 'FILED', CURRENT_TIMESTAMP
);
```

---

## IMPLEMENTATION STEPS

### Step 1: Create New Seed Script
**File**: `services/data/seed_varied_risks.py`

```python
def create_high_risk_shipments():
    """Create 20 high-risk shipments (90-99% expected score)"""
    # Element 9 mismatches
    # OFAC matches
    # UFLPA controlled goods
    # Multiple shipper shells
    
def create_medium_risk_shipments():
    """Create 30 medium-risk shipments (60-70% expected score)"""
    # New shippers
    # Dwell anomalies
    # AD/CVD corridors
    
def create_low_risk_shipments():
    """Create 50 low-risk shipments (<50% expected score)"""
    # Established shippers
    # Clean documentation
    # Standard corridors
```

### Step 2: Update risk_score Calculation
**File**: `services/data/db.py` → `get_shipments()` function

Currently, it orders by pre-stored `risk_score`:
```python
ORDER BY COALESCE(risk_score, 0) DESC
```

**After**: Keep ordering but populate risk_score dynamically:
```python
# On-demand calculation via API
# Or fetch from cache if recently calculated
ORDER BY COALESCE(risk_score, 0) DESC
```

### Step 3: Update API Response
**File**: `services/api/main.py` → `list_shipments()` endpoint

Include risk_score from comprehensive calculation:
```python
# Fetch shipment basic data
shipment = get_shipment(shipment_id)

# Calculate risk dynamically (cached for 1 hour)
risk_result = await _calculate_comprehensive_risk(shipment_id)
shipment['risk_score'] = risk_result['risk_breakdown']['final_score']

return shipment
```

### Step 4: Update Database Query
**Option A: Keep risk_score column but populate dynamically**
```sql
UPDATE shipments SET risk_score = <calculated_score> WHERE shipment_id = ?
-- Run after comprehensive scoring
```

**Option B: Remove risk_score column entirely**
```sql
ALTER TABLE shipments DROP COLUMN risk_score;
-- Calculate on-demand only
```

---

## VALIDATION CHECKLIST

After seeding:
- [ ] High-risk shipments (95%+) have:
  - Element 9 mismatch OR multiple red flags
  - China/Vietnam origin OR OFAC match
  - Expected score: Call `/api/risk-scoring/comprehensive` → verify score >= 90
  
- [ ] Medium-risk shipments (60-70%):
  - New shipper OR dwell anomaly OR AD/CVD exposure
  - Expected score: 60-70 from comprehensive API
  
- [ ] Low-risk shipments (<50%):
  - Established shipper, clean docs, standard corridor
  - Expected score: < 50 from comprehensive API

- [ ] Altana API called for risk >= 80:
  - Check audit_trail in comprehensive response
  - Verify altana_response is populated

---

## WORKFLOW VISUALIZATION

```
USER OPENS INVESTIGATION
    ↓
UI FETCHES CASE WITH shipment_id
    ↓
Case shows shipment basic info
    ↓
USER CLICKS "RISK SCORING" TAB
    ↓
Hook calls /api/risk-scoring/comprehensive
    ↓
API calculates 17 components:
  - Documentation (ISF, Element 9, manifest)
  - Corridor (CN→US vs CA→US)
  - Commodity (HS code, AD/CVD)
  - Routing (dwell, ports, vessel)
  - Party (shipper age, OFAC, ownership)
  - Pattern (price variance, frequency)
  - Time (pre-tariff timing, seasonal)
    ↓
If score >= 80:
  - Call ALTANA API for verification
  - Get supply chain risk assessment
  - Adjust final score if needed
    ↓
Return final_score with audit trail
    ↓
UI displays:
  - 7-factor breakdown
  - Component scores
  - Altana validation status
  - Adjustment reason
```

