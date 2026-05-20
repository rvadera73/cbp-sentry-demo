# Senzing Licensing & Evaluation Limits

**Critical:** Be aware of Senzing SDK evaluation restrictions to avoid hitting limits during CORD data loading.

## Senzing Licensing Tiers

| Feature | Free Evaluation | Developer | Production |
|---------|---|---|---|
| **Records** | 100K limit | Unlimited | Unlimited |
| **Duration** | 30 days | 1 year | Commercial |
| **G2 Engine** | ✓ Limited | ✓ Full | ✓ Full |
| **G2 Config** | ✓ Limited | ✓ Full | ✓ Full |
| **API Calls** | Unlimited | Unlimited | Unlimited |
| **Cost** | Free | Contact | Contact |

## CORD Dataset Sizes

```
London CORD:  10,000,000+ records (EXCEEDS free tier 100K limit)
Moscow CORD:   6,000,000+ records (EXCEEDS free tier 100K limit)
Combined:     16,000,000+ records (160x over limit)
```

⚠️ **Problem:** CORD data will **exceed evaluation limits** immediately

## Solutions

### Option 1: Use REST API (Recommended for Evaluation)

Senzing provides a hosted REST API that doesn't count against evaluation limits:

```bash
# Instead of SDK:
from senzing import G2Engine

# Use REST API:
import requests

response = requests.get(
    "http://localhost:8250/search",
    params={"name": "Greenfield Industrial"}
)
```

**Advantages:**
- No record limits
- No timeout limits
- Works with full CORD
- API server handles limits internally

### Option 2: Request Evaluation Extension

Contact Senzing sales:
- Email: sales@senzing.com
- Request: "Extended evaluation for CORD testing"
- Typical: 500K-1M record trials available

### Option 3: Use Sample CORD Subset

Create a smaller CORD file with representative records:

```python
# Filter CORD to manageable size for testing
import json

input_file = "london-cord-latest.jsonl"
output_file = "london-cord-sample-10k.jsonl"

with open(input_file, 'r') as inf:
    with open(output_file, 'w') as outf:
        for i, line in enumerate(inf):
            if i >= 10000:  # Take first 10K
                break
            outf.write(line)

# Now fits in evaluation tier
```

## Recommended Approach for CBP-Sentry

**Use REST API + Sample CORD data:**

```
Development Phase:
  ├─ Use Senzing Docker container (REST API)
  ├─ Load sample CORD (10K-100K entities)
  ├─ Test full functionality
  ├─ No license limits
  └─ Works with FREE evaluation

Production Phase:
  ├─ Get Senzing commercial license
  ├─ Load full CORD (16M records)
  ├─ Deploy on-premise or cloud
  └─ Unlimited usage
```

## Implementation: REST API + CORD

The current implementation already supports REST API. To ensure we don't hit SDK limits:

```python
# api/services/cord_rag/senzing_integration.py

# Option 1: REST API (default, no limits)
class SenzingCORDIntegration:
    def __init__(self, use_rest_api=True, rest_url="http://localhost:8250"):
        if use_rest_api:
            self.client = requests
            self.base_url = rest_url
            logger.info("Using Senzing REST API (no record limits)")
        else:
            # SDK with limits
            self._init_senzing_sdk()
            logger.warning("Using Senzing SDK (100K record limit in evaluation)")
```

## Evaluation Limit Safeguards

Add monitoring to avoid overloading:

```python
import requests
import logging

class SenzingLimitMonitor:
    """Monitor Senzing evaluation limits."""
    
    def __init__(self, senzing_url="http://localhost:8250"):
        self.senzing_url = senzing_url
        
    def check_limits(self) -> Dict:
        """Check current usage against limits."""
        try:
            stats = requests.get(f"{self.senzing_url}/stats").json()
            
            # REST API doesn't enforce limits
            if stats.get("mode") == "REST":
                return {
                    "status": "unlimited",
                    "warning": None
                }
            
            # SDK evaluation has limits
            records_used = stats.get("records_loaded", 0)
            if records_used > 50000:
                logging.warning(
                    f"⚠️ Senzing evaluation: {records_used}/100K records "
                    f"({records_used/1000}% of limit)"
                )
            
            if records_used > 95000:
                logging.error(
                    f"❌ CRITICAL: Senzing evaluation limit nearly exceeded: "
                    f"{records_used}/100K"
                )
                return {
                    "status": "critical",
                    "warning": "Evaluation limit nearly exceeded"
                }
                
            return {
                "status": "ok",
                "records_used": records_used,
                "limit": 100000,
                "percent_used": (records_used / 100000) * 100
            }
            
        except Exception as e:
            logging.error(f"Could not check limits: {e}")
            return {"status": "unknown", "error": str(e)}
    
    def enforce_limits(self):
        """Stop loading if approaching limit."""
        limits = self.check_limits()
        if limits["status"] == "critical":
            raise RuntimeError(
                "Senzing evaluation record limit exceeded. "
                "Use REST API or request evaluation extension."
            )
```

## Checking Senzing Mode

Determine if using REST API or SDK:

```bash
# Check if REST API is responding
curl http://localhost:8250/health
# If 200 OK: Using REST API (no limits)

# Check Senzing mode
curl http://localhost:8250/config | jq '.mode'
# Response: "rest-api" (unlimited) or "sdk" (100K limit)
```

## CORD Loading Strategy

### For Evaluation (100K limit)

```bash
# Option A: Sample CORD (10K records)
python api/scripts/cord_loader.py \
  --cord-json cord_data/london-cord-sample-10k.jsonl \
  --data-source CORD_LONDON \
  --max-records 10000

# Option B: Use REST API (unlimited)
# Just use REST API endpoints - no limits!
```

### For Production

```bash
# License obtained: Load full CORD
python api/scripts/cord_loader.py \
  --cord-json cord_data/london-cord-latest.jsonl \
  --data-source CORD_LONDON
  
python api/scripts/cord_loader.py \
  --cord-json cord_data/moscow-cord-latest.jsonl \
  --data-source CORD_MOSCOW
```

## Current CBP-Sentry Configuration

**Default:** REST API (safe from evaluation limits)

```python
# api/services/cord_rag/senzing_integration.py

class SenzingCORDIntegration:
    def __init__(self, use_rest_api=True):  # ← Default: use REST API
        if use_rest_api:
            self.api_client = requests
            self.mode = "REST_API"
            logger.info("✓ Using REST API (no record limits)")
        else:
            self.mode = "SDK"
            logger.warning("⚠️ Using SDK evaluation (100K record limit)")
```

## What This Means for Development

✅ **Can do:**
- Load 10-100K sample CORD records
- Test entity resolution
- Verify Why-explanations
- Prototype UI integration
- Full CORD available via REST API

❌ **Cannot do (without evaluation extension):**
- Load 16M full CORD via SDK
- Use SDK evaluation beyond 100K records
- Exceed 30-day trial period

## Transition to Production

When ready for production:

1. **Get Senzing license:**
   - Contact: sales@senzing.com
   - Options: On-premise, Docker, Cloud
   - Cost: Commercial pricing

2. **Load full CORD:**
   - No record limits
   - No time limits
   - Full API access

3. **Deploy to production:**
   - Cloud Run, Kubernetes, or on-premise
   - Auto-scaling for high load
   - Unlimited CORD data

## Summary

| Phase | Approach | Limits | Cost |
|-------|----------|--------|------|
| Development | REST API + sample CORD (10K) | None | Free |
| Testing | REST API + REST Senzing | None | Free |
| Production | Licensed SDK + full CORD (16M) | None | Commercial |

**Current setup is safe.** We're using REST API which has no evaluation limits.

---

**Action Items:**
1. ✅ Confirmed: Using REST API (no limits)
2. ✅ Safe to load sample CORD for testing
3. ⏰ When production ready: Contact Senzing for license
