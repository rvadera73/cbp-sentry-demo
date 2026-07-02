# NoSQL Rules Engine Research: Complete Analysis

**Date:** June 12, 2026  
**Context:** CBP Sentry Risk Scoring Rules Engine - Local Development + Production Scaling  
**Scope:** Multi-analyst parameter versioning, audit trails, concurrent access patterns

---

## Executive Summary

**Recommendation for CBP Sentry:**

| Layer | Technology | Rationale |
|-------|-----------|-----------|
| **Local Dev** | SQLite (JSON1) + Git | Zero setup, version control built-in, file-based versioning |
| **Rules (Code)** | Git-versioned YAML/JSON | Immutable audit trail, code review workflow, cheap to scale |
| **Parameters (Data)** | Firebase Firestore free tier | Simple admin UI, free tier scales to 10K daily requests, built-in versioning |
| **Audit Trail** | Append-only collection in Firestore | Immutable events, temporal queries, query-as-of-date capability |
| **Multi-Analyst Safety** | Optimistic concurrency control (version field) | Last-write-wins with conflict detection, safe simultaneous edits |

**Cost at 1000 shipments/day:** ~$0 on Firestore free tier indefinitely (50K reads + 20K writes daily = 500K reads + 200K writes monthly).

---

## Part 1: Local Development Databases

### 1.1 SQLite with JSON1 Extension

**Setup:** 0 minutes (ships with most Python/Node installations)

```bash
# Python example
import sqlite3
conn = sqlite3.connect(':memory:')  # or 'rules.db'
cursor = conn.cursor()
cursor.execute('SELECT json_valid(?)', ('{"rule_id": "001"}',))
```

**Storage & Features:**
- **Size Limits:** Unlimited in theory; practical limit ~280 TB per file
- **File Size:** Single `.db` file commits cleanly to Git
- **JSON1 Capability:** Built-in as of SQLite 3.38.0 (Feb 2022)
  - JSON extraction: `json_extract(json_col, '$.rule.weight')`
  - JSON modification: `json_set(json_col, '$.status', 'active')`
  - Full-text search on JSON: with FTS5 extension

**Versioning & Audit:**
- **Version Control:** `.db` file diffs with `git` are binary (non-readable)
- **Alternative:** Export to YAML/JSON before commit (readable history)
- **Time Travel Queries:** Use MVCC (Multi-Version Concurrency Control)
  - Example: Create `audit_events` table, append immutable records
  - Query: `SELECT * FROM audit_events WHERE timestamp <= ?` → reconstruct state

**Example Audit Pattern:**
```sql
CREATE TABLE rule_audit (
  event_id INTEGER PRIMARY KEY,
  rule_id TEXT NOT NULL,
  change_type TEXT, -- INSERT, UPDATE, DELETE
  old_value JSON,
  new_value JSON,
  analyst TEXT,
  timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
  checksum TEXT -- hash of previous event (blockchain-style)
);

-- Query: "What was rule 001 on June 1?"
SELECT * FROM rule_audit 
WHERE rule_id = '001' 
AND timestamp <= '2026-06-01 23:59:59'
ORDER BY timestamp DESC 
LIMIT 1;
```

**Concurrent Access:**
- **Locking Model:** SQLite uses database-level locks (coarse-grained)
- **Conflict:** If analyst A and B save simultaneously on same rule:
  - One gets SQLITE_BUSY (must retry)
  - Not suitable for high-concurrency scenarios
- **Optimistic Concurrency:** Can add `version` column; check before update
  ```sql
  UPDATE rules SET value = ?, version = version + 1 
  WHERE rule_id = ? AND version = ?;
  ```
  If 0 rows updated, conflict detected (analyst B already changed it).

**Audit Trail Costs:** Negligible (append-only table in same `.db` file)

**Verdict:**
- ✅ **Best for:** Local development, testing, configuration schema versioning in Git
- ❌ **Not for:** Production multi-user writes (locking), high-concurrency parameter updates
- 💾 **Storage Cost:** $0 (local file)

---

### 1.2 MongoDB Community Edition

**Setup:** 5-10 minutes (Docker or local binary)

```bash
docker run -d -p 27017:27017 --name mongo mongo:latest
```

**Storage & Features:**
- **Data:** Stores BSON (binary JSON) documents
- **Size Limits:** None (file grows as needed)
- **Built-in Audit:** Yes, but only in Enterprise Edition
- **Community Edition:** No audit logging; must implement in application

**Versioning:**
- **Document Versioning:** Add `_version` field, manage in app
  ```javascript
  db.rules.updateOne(
    { rule_id: "001", _version: 5 },
    { $set: { weight: 0.75, _version: 6, updated_by: "analyst_a" } }
  );
  ```
  If version mismatch → 0 rows updated → conflict detected
- **Audit Trail:** Manual: create `audit_log` collection, trigger on every update

**Concurrent Access:**
- **Model:** MVCC + optimistic concurrency (via version field)
- **Atomic Operations:** Document-level (not multi-document without transactions)
- **MongoDB 4.0+:** Multi-document ACID transactions available
  - Add version check + update + audit log in single transaction
  - Safe for concurrent analyst edits

**Local vs Production:**
- Community Edition: Excellent for local dev
- Atlas Free (M0 Tier): 0.5 GB storage, no backups, **NO audit logging**
  - Upgrade to M10: $57/month for basic audit + backups
  - Not cost-effective for rules engine (overkill features, expensive audit tier)

**Verdict:**
- ✅ **Best for:** Local development (free, featureful)
- ❌ **Not for:** Free production (no audit), paid production (too expensive vs Firestore)
- 💾 **Community Setup Cost:** $0; Atlas M0: $0; Atlas M10+ (audit): $57+/month

---

### 1.3 Embedded: RocksDB, LevelDB

**Setup:** ~5 minutes via Docker or language SDK

**Storage & Features:**
- **RocksDB (Facebook):** Key-value store, LSM tree, ultra-fast writes
- **LevelDB (Google):** Lightweight KV store, simpler than RocksDB
- **Size:** Unlimited (local SSD)
- **Snapshots:** Supported (point-in-time recovery)
- **Write-Ahead Logging (WAL):** Durability built-in; can recover after crash

**Versioning & Audit:**
- **Snapshot Capability:** Can take consistent snapshot at any point
  - Example: `snapshot_1 = db.get_snapshot()` at T=2026-06-01 12:00
  - Query as-of-snapshot: `db.get("rule_001", snapshot=snapshot_1)`
- **Audit Trail:** No built-in audit logging
  - Must implement: log every write to separate KV range
  - Example: `db.put("audit:2026-06-01:12:00:01", { rule_id, change_type, new_value })`
- **Versioning:** No automatic document versioning; manage in app

**ACID & Concurrent Access:**
- **Transactions:** Basic (not full ACID)
- **Concurrency:** Single writer at a time (WriteLocked)
  - Multiple readers OK
  - Analyst A and B: only one can write simultaneously
  - Not suitable for multi-analyst parameter edits without queueing

**Verdict:**
- ✅ **Best for:** Embedded in single-writer applications (e.g., ETL, batch jobs)
- ❌ **Not for:** Multi-analyst concurrent edits, production audit trails (manual implementation)
- 💾 **Cost:** $0 (embedded)

---

### 1.4 Redis (In-Memory with Persistence)

**Setup:** 3 minutes (Docker: `docker run -d -p 6379:6379 redis:latest`)

**Storage & Features:**
- **In-Memory KV:** Ultra-fast reads/writes (~100K ops/sec single thread)
- **Persistence Options:**
  - **RDB:** Point-in-time snapshots (fast but coarse-grained)
  - **AOF (Append-Only File):** Every write logged (audit trail!)
  - **Hybrid (4.0+):** RDB + AOF combined

**Audit Trail via AOF:**
- **How It Works:** Every write appended to `.aof` file
  ```
  *3
  $3
  SET
  $7
  rule:01
  $25
  {"weight":0.75,"status":"active"}
  ```
- **Queryability:** AOF is append-only but not queryable (just log)
- **Replay:** Can replay AOF to reconstruct state at any point in time
  - Requires app-level logic to parse AOF and answer "what was rule_001 on June 1?"

**12-Month Retention:**
- AOF grows unbounded → compacted via `BGREWRITEAOF` (reduces size)
- Example retention: Keep daily RDB snapshots for 12 months
  - Cost: 30 snapshots/month × 12 months = 360 snapshots
  - Each snapshot ≈ dataset size
  - For 1 GB parameters: 360 GB storage for 12-month history
  - **Not practical for long-term audit trails**

**Concurrent Access:**
- **Single-Threaded:** All writes queued
- **Conflict Prevention:** Built-in (last-write-wins, atomic INCR/LPUSH)
- **Watch (Optimistic Locking):** `WATCH rule:01` + transaction
  - Analyst A and B both WATCH same key
  - Only one transaction commits; other gets error (must retry)

**Verdict:**
- ✅ **Best for:** Cache layer, session storage, real-time analytics
- ❌ **Not for:** Rules engine primary storage (no queryable audit, poor retention economics)
- 💾 **Cost:** Redis Cloud free tier = 30 MB (too small); paid = $7+/month

---

## Part 2: Managed Services (Production Free Tiers)

### 2.1 Firebase Firestore

**Free Tier (Spark Plan):**
- **Reads:** 50,000 daily
- **Writes:** 20,000 daily
- **Deletes:** 20,000 daily
- **Storage:** 1 GB total
- **Cost:** $0 indefinitely (no credit card required)

**Paid Tier (Blaze Plan - pay-as-you-go):**
- Reads: $0.06 per 100K
- Writes: $0.18 per 100K
- Deletes: $0.02 per 100K
- Storage: $0.18 per GB/month
- **Important:** No hard spending cap (can spike to $1000s if code has bug)

**Scaling to 1000 Shipments/Day:**
- **Assumption:** ~5 API calls per shipment (fetch rules + params, log eval, update risk score)
  - 1000 shipments × 5 calls = 5000 daily requests
  - ≈ 3500 reads + 1000 writes + 500 deletes
  - **Result:** Well within free tier (never triggers billing)
- **Assumption:** ~10 calls per shipment
  - 10,000 daily requests: still within free tier
- **Assumption:** ~25 calls per shipment
  - 25,000 reads + 5000 writes + 2500 deletes
  - Approaching/at limits (risk of overage charges)

**Document Versioning:**
```javascript
// rules_engine/rules/{rule_id}
{
  rule_id: "WEIGHT_CALC_001",
  active_version: 5,
  version: 5,
  weight: 0.75,
  updated_by: "analyst_a",
  updated_at: "2026-06-12T10:30:00Z"
}

// rules_engine/rule_versions/{rule_id}/{version}
{
  version: 4,
  weight: 0.70,
  created_by: "analyst_a",
  created_at: "2026-06-11T14:20:00Z"
}
```

**Audit Trail (Append-Only):**
```javascript
// rules_engine/audit_events/{auto_id}
{
  event_id: "evt_...",
  rule_id: "WEIGHT_CALC_001",
  event_type: "RULE_UPDATED",
  old_value: { weight: 0.70 },
  new_value: { weight: 0.75 },
  analyst: "analyst_a@cbp.gov",
  timestamp: "2026-06-12T10:30:00Z"
  // This document is write-once, never modified
}
```

**Temporal Queries ("What was rule X on date Y?"):**
```javascript
// Get all events for rule X before date Y
const snapshot = await db
  .collection('rules_engine/audit_events')
  .where('rule_id', '==', 'WEIGHT_CALC_001')
  .where('timestamp', '<=', new Date('2026-06-01'))
  .orderBy('timestamp', 'desc')
  .limit(1)
  .get();
  
// Reconstruct state by replaying events from timestamp 0
```

**Concurrent Multi-Analyst Updates (Optimistic Concurrency):**
```javascript
// Analyst A: Fetch current version
const doc = await db.collection('rules').doc('WEIGHT_CALC_001').get();
const currentVersion = doc.data().version; // = 5

// Analyst B: Simultaneously fetch (also sees version 5)

// Analyst A: Updates to version 6
await db.collection('rules').doc('WEIGHT_CALC_001').update({
  weight: 0.75,
  version: 6,
  updated_by: 'analyst_a'
});

// Analyst B: Tries to update with old version
try {
  await db.collection('rules').doc('WEIGHT_CALC_001').update({
    weight: 0.80,
    version: 6,  // Firestore will check conditional write via transaction
    updated_by: 'analyst_b'
  });
} catch (e) {
  // Conflict: version already 6, must re-fetch and retry
}
```

**Audit Trail Retention (12+ Months):**
- Append-only design: events never deleted
- 1000 shipments/day × 365 days = 365K events/year
- Each event ≈ 500 bytes
- Total: 365K × 500 B ≈ 183 MB/year (negligible)
- **Cost:** Included in $0.18/GB/month storage (pay-as-you-go tier)
- **Querying:** Via Firestore queries (instant retrieval)

**Verdict:**
- ✅ **Best for:** Rules engine parameters + audit trail (free forever at scale)
- ✅ **Multi-analyst safe:** Built-in optimistic concurrency
- ✅ **Versioning:** Easy (document-level + subcollection for history)
- ⚠️ **Risk:** No spending cap (set billing alerts)
- 💾 **Cost:** $0 indefinitely (1000s shipments/day free)

---

### 2.2 MongoDB Atlas Free Tier (M0)

**Free Tier (M0 - formerly "Free Cluster"):**
- **Storage:** 0.5 GB (hard limit, cannot exceed)
- **Backups:** None available
- **Audit Logging:** None available (Enterprise Edition only, M10+)
- **Regions:** 3 (replicated automatically)
- **Cost:** $0

**Upgrade Path to Paid:**
- **M10 (Starter):** $57/month
  - 10 GB storage
  - Daily backups
  - **Audit Logging:** Available (charges extra)
- **Upgrade Cost:** $57/month → $300+/month with audit logging

**0.5 GB Limit for Rules Engine:**
- Rules collection: ~100 rules × 5 KB = 500 KB
- Parameter history: ~100 rules × 50 versions × 1 KB = 5 MB
- Audit trail: ~10 events/day × 365 days × 2 KB = 7.3 MB
- Total: ~13 MB (fits in 0.5 GB)
- **but:** Hard limit means no growth capacity; delete old audit data after 12 months

**Concurrent Multi-Analyst Updates:**
```javascript
// Optimistic concurrency with version field
db.collection('rules').updateOne(
  { rule_id: 'WEIGHT_CALC_001', version: 5 },
  { $set: { weight: 0.75, version: 6, updated_by: 'analyst_a' } }
);
// If version ≠ 5, update fails; app must retry
```

**Audit Trail & Versioning:**
- Backups not available on free tier
- Manual versioning: store old docs in `rule_versions` collection
- Audit events: append-only collection (not deleted)

**Verdict:**
- ✅ **Best for:** Prototyping, small-scale local deployment
- ❌ **Not for:** Production (0.5 GB limit, no audit logging in free tier)
- ❌ **Cost Trap:** Audit logging requires $300+/month (expensive)
- 💾 **Cost:** $0 tier; $57+/month if upgrading

---

### 2.3 AWS DynamoDB

**Free Tier (Always Free - never expires):**
- **Storage:** 25 GB per month (averaged)
- **Read Capacity Units (RCU):** 25 units/second
- **Write Capacity Units (WCU):** 25 units/second
- **DynamoDB Streams:** 2.5 million reads from streams
- **Cost:** $0 (included forever)

**On-Demand Pricing (if exceeding free tier):**
- Reads: $0.25 per 1M requests
- Writes: $1.25 per 1M requests
- Storage: $0.25/GB for on-demand
- **Standard-IA (Infrequent Access) for audit trails:** $0.10/GB/month (37.5% cheaper)

**Scaling to 1000 Shipments/Day:**
- Assumptions: 5 reads + 2 writes per shipment
- Daily: 5K reads + 2K writes
- Monthly: 150K reads + 60K writes
- **Free tier quota:** 25 RCU/sec = 2.16M reads/month (25GB × 86400 seconds / month conversion)
- **Result:** Well within free tier

**DynamoDB Streams for Audit Trail:**
- **How It Works:** Streams capture every write/update/delete as an event
  ```
  Record 1: { rule_id: "001", weight: 0.70 } → NEW_IMAGE
  Record 2: { rule_id: "001", weight: 0.75 } → MODIFIED (old & new)
  Record 3: { event_id: "evt_001", ... } → NEW_IMAGE
  ```
- **Stream Reads:** 2.5M included in free tier (enough for audit trail)
- **Query-as-of-Date:** Requires app logic
  - Store timestamp in stream events
  - Replay stream up to target date → reconstruct state

**Concurrent Multi-Analyst Updates:**
```javascript
// Option 1: Optimistic Concurrency (conditional write)
const params = {
  TableName: 'rules',
  Key: { rule_id: { S: 'WEIGHT_CALC_001' } },
  UpdateExpression: 'SET #w = :weight, #v = :newVersion',
  ConditionExpression: '#v = :oldVersion',
  ExpressionAttributeNames: {
    '#w': 'weight',
    '#v': 'version'
  },
  ExpressionAttributeValues: {
    ':weight': { N: '0.75' },
    ':newVersion': { N: '6' },
    ':oldVersion': { N: '5' }
  }
};
// If version ≠ 5, ConditionalCheckFailedException; app must retry
```

**Audit Trail (12+ Months):**
- Streams only retain events for 24 hours
- To archive: Lambda function reads stream → writes to S3 (audit archive table)
- S3 cost: $0.023/GB/month (cheap long-term storage)
- 365K audit events × 500B = 183 MB/year = ~$0.004/year (negligible)

**Verdict:**
- ✅ **Good for:** Rules engine with audit trails via Streams
- ✅ **Scales to 1000s daily requests** (free tier covers it)
- ⚠️ **Setup Complexity:** Streams → Lambda → S3 for audit archival (moderate)
- ⚠️ **Query Complexity:** Temporal queries require stream replay or DynamoDB Query API
- 💾 **Cost:** $0 at scale (1000s/day), S3 archive: ~$0.01/year

---

### 2.4 Google Cloud Firestore (Native Mode)

**Free Tier (Spark Plan):**
- **Reads:** 50,000 daily
- **Writes:** 20,000 daily
- **Deletes:** 20,000 daily
- **Storage:** 1 GB
- **Cost:** $0 (same as Firebase Firestore)

**Difference from Firebase Firestore:**
- Both are Google Cloud Firestore; Firebase is just the web/mobile interface
- **Native Mode (GCP Console):** Full query capabilities, advanced indexing
- **Datastore Mode (legacy):** Limited query support
- **Recommendation:** Use Firestore Native Mode (same as Firebase Firestore)

**Verdict:**
- ✅ **Identical to Firebase Firestore** (see section 2.1)
- 💾 **Cost:** $0 indefinitely

---

### 2.5 Azure Cosmos DB

**Free Tier (Lifetime):**
- **Throughput:** 1000 RU/sec
- **Storage:** 25 GB
- **Cost:** $0 indefinitely (lifetime free tier)

**RU (Request Unit) Calculation:**
- 1 RU = cost to read 1 KB document
- Write = 2x-3x read cost
- Example: 1000 shipments/day × 5 ops × 2 KB avg = 10K KB = 10K RUs
- Free tier = 1000 RU/sec = 86.4M RU/month → easily covers 10K RU/day

**Scaling to 1000 Shipments/Day:**
- **Result:** Well within free tier

**Optimistic Concurrency (ETag-based):**
```csharp
// Fetch document with ETag
var document = await container.ReadItemAsync<Rule>("WEIGHT_CALC_001", new PartitionKey("rules"));
var etag = document.ETag; // "abc123"

// Update with ETag condition
try {
  await container.ReplaceItemAsync(
    new Rule { weight = 0.75, version = 6 },
    "WEIGHT_CALC_001",
    new PartitionKey("rules"),
    new ItemRequestOptions { IfMatchEtag = etag }
  );
} catch (CosmosException e) {
  if (e.StatusCode == HttpStatusCode.PreconditionFailed) {
    // Conflict: ETag changed, must retry
  }
}
```

**Audit Trail & Versioning:**
- No built-in audit logging (must implement in app)
- Append-only pattern: create `audit_events` collection
- Temporal queries: filter by timestamp, reconstruct state

**Retention (12+ Months):**
- Append-only design: events never deleted (RU cost for storage)
- 365K events × 2 KB = 730 MB/year
- Cost: included in 25 GB free storage (lifetime)

**Verdict:**
- ✅ **Good for:** Rules engine with free tier parity to Firestore
- ✅ **Scales indefinitely** (free tier larger than Firestore)
- ⚠️ **RU Model:** More complex than read/write pricing (requires mental conversion)
- ✅ **Multi-API Support:** SQL, MongoDB, Cassandra, Gremlin, Table (flexible)
- 💾 **Cost:** $0 indefinitely (1000s/day free)

---

### Summary: Managed Services Comparison

| Service | Free Tier | Audit Logging | Versioning | Multi-Analyst Safe | Cost at 1000/day |
|---------|-----------|---|---|---|---|
| **Firestore** | 50K R/20K W/20K D/1GB | Manual (append-only) | Document-level | ✅ (optimistic) | $0 |
| **MongoDB Atlas M0** | 0.5 GB | ❌ (need M10+) | Manual | ✅ (optimistic) | $0 ($300+ with audit) |
| **DynamoDB** | 25GB/25RCU/25WCU | Streams (24h retention) | Manual | ✅ (conditional) | $0 (+ $0.01 S3 archive) |
| **Cosmos DB** | 1000 RU/25GB | Manual (append-only) | Manual | ✅ (ETag) | $0 |
| **GCP Firestore** | Same as Firebase | Manual (append-only) | Document-level | ✅ (optimistic) | $0 |

---

## Part 3: Hybrid Approach (Git + Managed DB)

### 3.1 Architecture Pattern

**Separation of Concerns:**

```
git (immutable, code review required)
├── rules/ (rule definitions, versioned)
│   ├── risk_scoring/
│   │   ├── weight_calculation.yaml
│   │   ├── compliance_rules.json
│   │   └── history/  (archive of old versions)
│   └── manifests/  (manifest enrichment rules)
│
└── RULE_CHANGELOG.md (human-readable version history)

Firestore (transactional, real-time updates)
├── rules_engine/rules/ (current parameter values)
├── rules_engine/rule_versions/ (historical parameter versions)
├── rules_engine/audit_events/ (append-only event log)
└── parameters/ (analyst-driven adjustments, not in git)
```

### 3.2 Rule vs Parameter Distinction

**Rules (Git):**
- Rule logic, conditions, branching
- Example: "If manifest_risk_score > 0.7, escalate to high-risk"
- Change Frequency: Quarterly (needs code review)
- Deployment: Via CI/CD pipeline (semantic versioning)
- Audit Trail: Git commit history (who, when, why)

**Parameters (Firestore):**
- Numerical weights, thresholds, feature importance
- Example: "compliance_rule_weight = 0.75"
- Change Frequency: Daily (analysts adjust based on performance)
- Deployment: Real-time (no code deploy needed)
- Audit Trail: Firestore append-only events

**Example Parameter Change (No Code Deploy):**
```yaml
# git/rules/risk_scoring/weight_calculation.yaml (v1.2.3)
weights:
  compliance_score: {{ get_parameter('compliance_weight') }}
  manifest_risk: {{ get_parameter('manifest_risk_weight') }}
  vessel_history: {{ get_parameter('vessel_history_weight') }}

# Firestore/rules_engine/parameters
{
  compliance_weight: 0.75,  # Changed by analyst_a today
  manifest_risk_weight: 0.60,
  vessel_history_weight: 0.65
}

# When evaluating shipment:
rule_js = load_rule('risk_scoring/weight_calculation.yaml', version='1.2.3')
params = fetch_firestore_parameters()
score = evaluate(rule_js, params, shipment_data)
```

### 3.3 Sync Strategies

**Option A: Application Fetches Parameters at Runtime (Recommended)**

```python
# At app startup
rules = load_from_git('rules_scoring/weight_calculation.yaml', version='1.2.3')

# For each shipment evaluation
params = fetch_firestore_parameters()  # Real-time
score = evaluate_rule(rules, params, shipment)
```

- ✅ **Simplicity:** No background sync needed
- ✅ **Real-time:** Parameter changes apply instantly
- ⚠️ **Latency:** Extra Firestore fetch per shipment (adds ~5-10ms)
- **Cost:** 1 extra read per shipment

**Option B: Webhook-Driven Updates (When Parameter Changes)**

```python
# In Firestore, set Cloud Functions trigger
@firestore.on_update('parameters/*')
def sync_parameters_to_cache(change, context):
  # Analyst updates weight in Firestore
  params = change.after.get()
  # Publish to Redis/in-memory cache
  cache.update('rule_params', params)
  # Notify app via webhook or pub/sub
  publish('parameters-updated', params)

# App subscribes to updates
pubsub.subscribe('parameters-updated', on_parameters_updated)

# Evaluation uses local cache (no Firestore fetch)
score = evaluate_rule(rules, local_cache['rule_params'], shipment)
```

- ✅ **Low Latency:** Evaluation uses cached parameters
- ⚠️ **Complexity:** Requires webhooks, pub/sub, cache invalidation
- ✅ **Scalability:** Thousands of shipments without extra Firestore reads

**Option C: Git-Driven Parameter Updates (Slowest)**

```yaml
# git/rules/parameters.yaml (versioned, semantic versioning)
parameters:
  compliance_weight: 0.75  # v1.3.0 (deployed 2026-06-12)
  manifest_risk_weight: 0.60
```

- ❌ **Slow:** Parameters only change when code deploys (daily/weekly)
- ❌ **Inflexible:** Analysts must file code review for parameter tweak
- ✅ **Auditable:** Full Git history of every parameter change
- **Not Recommended for dynamic rules engine**

**Recommended Hybrid Strategy:**
- Rules: Git-versioned YAML/JSON (quarterly releases)
- Parameters: Firestore (real-time updates by analysts)
- Sync: Application fetches parameters at runtime (Option A) or cache via webhooks (Option B)

---

## Part 4: Audit Trails & Version History

### 4.1 Append-Only Event Log Pattern

**Design (Firestore):**

```javascript
// Collection: rules_engine/audit_events (append-only)
{
  event_id: "evt_20260612_001",
  rule_id: "WEIGHT_CALC_001",
  event_type: "PARAMETER_UPDATED",
  
  // Immutable change record
  change: {
    analyst: "analyst_a@cbp.gov",
    timestamp: "2026-06-12T10:30:00.123Z",
    old_value: 0.70,
    new_value: 0.75,
    reason: "Performance tuning - reduced false positives by 2%"
  },
  
  // Blockchain-style chain
  previous_event_hash: "abc123...",  // SHA256 of previous event
  event_hash: "def456...",           // SHA256 of this event
  
  // Indexing for queries
  analyst: "analyst_a@cbp.gov",
  timestamp: "2026-06-12T10:30:00.123Z",
  rule_id: "WEIGHT_CALC_001"
}
```

**Key Properties:**
- **Immutable:** Document written once, never updated or deleted
- **Hashable:** Event hash chains to previous event (detect tampering)
- **Indexed:** Timestamps for temporal queries
- **Queryable:** Full-text search on change reason

### 4.2 Temporal Queries

**Query 1: "What was rule X's parameter on date Y?"**

```javascript
// Get last event before/at target date
const snapshot = await db
  .collection('rules_engine/audit_events')
  .where('rule_id', '==', 'WEIGHT_CALC_001')
  .where('timestamp', '<=', new Date('2026-06-01T23:59:59Z'))
  .orderBy('timestamp', 'desc')
  .limit(1)
  .get();

const lastEvent = snapshot.docs[0];
const valueOnJune1 = lastEvent.data().change.new_value;  // 0.70
```

**Query 2: "Show all parameter changes by analyst_a in June"**

```javascript
const snapshot = await db
  .collection('rules_engine/audit_events')
  .where('analyst', '==', 'analyst_a@cbp.gov')
  .where('timestamp', '>=', new Date('2026-06-01T00:00:00Z'))
  .where('timestamp', '<', new Date('2026-07-01T00:00:00Z'))
  .orderBy('timestamp', 'desc')
  .get();

snapshot.forEach(doc => {
  console.log(`${doc.data().change.timestamp}: ${doc.data().change.old_value} → ${doc.data().change.new_value}`);
});
```

**Query 3: "Reconstruct full rule state as of date X"**

```javascript
async function getRuleStateAsOf(ruleId, targetDate) {
  const events = await db
    .collection('rules_engine/audit_events')
    .where('rule_id', '==', ruleId)
    .where('timestamp', '<=', targetDate)
    .orderBy('timestamp', 'asc')
    .get();

  let state = {};
  events.forEach(doc => {
    const change = doc.data().change;
    state[change.field] = change.new_value;  // or entire object
  });
  
  return state;
}

const juneState = await getRuleStateAsOf('WEIGHT_CALC_001', new Date('2026-06-30'));
```

### 4.3 Storage Costs (12+ Months)

**Estimate:**
- Shipments/day: 1000
- Analyst parameter changes/shipment: 0.01 (1 change per 100 shipments)
- Daily parameter changes: 10
- Audit events/change: 1
- **Daily audit events: 10**
- **Monthly: 300**
- **Yearly: 3,600**

**Storage:**
- Per event: ~500 bytes (rule_id, analyst, timestamp, old_value, new_value, reason)
- 3,600 events × 500 B = 1.8 MB/year

**Cost:**
- Firestore Storage: $0.18/GB/month
- 1.8 MB ≈ negligible (included in 1 GB free tier)

**Queryability:** Firestore indexes for temporal queries (included in free tier)

---

## Part 5: Multi-Analyst Concurrent Access

### 5.1 Problem Scenario

**Analyst A (10:30 AM):**
1. Fetches rule WEIGHT_CALC_001, sees version = 5, weight = 0.70
2. Thinks: "Let me increase to 0.75"
3. Submits update

**Analyst B (10:30:05 AM):**
1. Fetches same rule, sees version = 5, weight = 0.70
2. Thinks: "Let me decrease to 0.65"
3. Submits update

**Without Concurrency Control:** Last-write-wins
- Analyst A saves first: weight = 0.75, version = 6
- Analyst B saves second: weight = 0.65, version = 6 (overwrites A's change)
- **Result:** Analyst A's change lost (BAD)

### 5.2 Optimistic Concurrency Control

**Solution: Version Field Check**

```javascript
// Analyst A's update
await db.collection('rules').doc('WEIGHT_CALC_001').update({
  weight: 0.75,
  version: 6,  // Increment version
  updated_by: 'analyst_a'
});
// Firestore transaction: "Update only if current version is 5"
// Success: weight = 0.75, version = 6

// Analyst B's update (still has old version = 5 in memory)
try {
  await db.collection('rules').doc('WEIGHT_CALC_001').update({
    weight: 0.65,
    version: 6,
    updated_by: 'analyst_b'
  });
} catch (e) {
  // Firestore: "Current version is 6, not 5 - conditional write failed"
  // App shows error: "Rule was modified by another analyst. Please refresh."
  // Analyst B refetches, sees new version, tries again
}
```

**Firestore Implementation (Transaction):**

```javascript
await db.runTransaction(async (transaction) => {
  const docRef = db.collection('rules').doc('WEIGHT_CALC_001');
  const docSnap = await transaction.get(docRef);
  const currentVersion = docSnap.data().version;

  if (currentVersion !== expectedVersion) {
    throw new Error('Version mismatch - rule was modified');
  }

  transaction.update(docRef, {
    weight: newWeight,
    version: currentVersion + 1,
    updated_by: analyst_email
  });
});
```

### 5.3 Conflict Resolution Strategies

**Strategy 1: Retry (Last-Write-Wins)**
- Analyst B gets error, refetches, tries again
- Simple but loses one analyst's change
- **Suitable for:** Parameters with clear "latest value" (e.g., weight)

**Strategy 2: Merge (If Possible)**
- If Analyst A changed weight, Analyst B changed threshold
  - Both changes can apply (no conflict)
- Requires field-level conflict detection (complex)
- **Suitable for:** Multi-field updates

**Strategy 3: Lock (Pessimistic)**
- Analyst A locks rule when fetching: "I'm editing this"
- Analyst B sees lock, waits or gets error
- Analyst A releases lock after update
- **Suitable for:** Low-frequency updates (quarterly rule changes)

**Recommendation for Rules Engine:**
- **Parameters (weight, threshold):** Strategy 1 (retry)
  - Simplicity: "Last analyst's value wins"
  - Analyst B retries after seeing conflict
- **Rules (conditions, logic):** Strategy 3 (lock)
  - Rules change rarely (quarterly)
  - Lock prevents two analysts from simultaneously refactoring same rule

### 5.4 Multi-User Safety Checklist

| Concern | Implementation | Result |
|---------|---|---|
| **Lost Updates** | Version field + conditional writes | ✅ Conflict detected |
| **Dirty Reads** | Read-after-write consistency | ✅ Analyst sees own changes immediately |
| **Stale Reads** | Firestore real-time listeners | ✅ App notified when rule changes |
| **Audit Trail** | Append-only events collection | ✅ Full history of who changed what |
| **Rollback** | Previous versions in rule_versions subcollection | ✅ Revert to any historical version |

---

## Part 6: Recommendations for CBP Sentry

### 6.1 Recommended Architecture

```
┌─────────────────────────────────────────────────┐
│ Local Development (Developer Laptop)             │
├─────────────────────────────────────────────────┤
│ SQLite (risk_scoring.db)                        │
│ + Git-versioned YAML rule definitions           │
│ + Minimal audit trail (for testing)             │
└─────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────┐
│ Production (Staging & Live)                      │
├─────────────────────────────────────────────────┤
│ ┌─────────────────────────────────────────────┐ │
│ │ Git Repository (Rules Code)                  │ │
│ │ ├── rules/risk_scoring/*.yaml               │ │
│ │ ├── rules/manifests/*.json                  │ │
│ │ └── RULE_CHANGELOG.md                       │ │
│ └─────────────────────────────────────────────┘ │
│                    ↓ (CI/CD)                     │
│ ┌─────────────────────────────────────────────┐ │
│ │ Firestore Collection: rules_engine          │ │
│ │ ├── /rules/{rule_id}                        │ │
│ │ │   ├── rule_id, active_version, weight    │ │
│ │ │   └── updated_by, timestamp               │ │
│ │ ├── /rule_versions/{rule_id}/{version}     │ │
│ │ │   └── Historical versions                 │ │
│ │ ├── /parameters/{param_id}                 │ │
│ │ │   ├── value, analyst, timestamp           │ │
│ │ │   └── reason (optional)                   │ │
│ │ └── /audit_events/{auto_id}                │ │
│ │     ├── event_type, change, analyst        │ │
│ │     ├── timestamp, previous_event_hash     │ │
│ │     └── (append-only, never modified)      │ │
│ └─────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────┘
        ↑ Real-time parameter updates from analysts ↑
```

### 6.2 Data Model (Firestore)

```javascript
// Database: Default (or create 'risk-scoring-db')
// Collections:

// 1. rules_engine/rules/{rule_id}
{
  rule_id: "WEIGHT_CALC_001",
  name: "Weight Calculator",
  active_version: "1.2.3",  // Semantic version (deployed via Git)
  
  // Current parameter values (analysts update these)
  parameters: {
    compliance_weight: 0.75,
    manifest_risk_weight: 0.60,
    vessel_history_weight: 0.65
  },
  
  metadata: {
    created_at: "2026-05-01T00:00:00Z",
    last_modified_at: "2026-06-12T10:30:00Z",
    last_modified_by: "analyst_a@cbp.gov",
    version: 5  // For optimistic concurrency control
  }
}

// 2. rules_engine/rule_versions/{rule_id}/{version_id}
// (Archive of historical parameter values)
{
  version: 5,
  parameters: {
    compliance_weight: 0.70,
    manifest_risk_weight: 0.60,
    vessel_history_weight: 0.65
  },
  created_at: "2026-06-11T14:20:00Z",
  created_by: "analyst_a@cbp.gov",
  reason: "Baseline from Git release v1.2.3"
}

// 3. rules_engine/parameters/{param_id}
// (For parameters that span multiple rules)
{
  param_id: "VESSEL_RISK_THRESHOLD",
  name: "Vessel Risk Threshold",
  value: 0.75,
  datatype: "float",
  
  metadata: {
    last_modified_at: "2026-06-12T10:30:00Z",
    last_modified_by: "analyst_a@cbp.gov",
    reason: "Tuning after false positive review",
    version: 3
  }
}

// 4. rules_engine/audit_events/{auto_id}
// (Append-only event log - immutable after creation)
{
  event_id: "evt_20260612_001",
  event_type: "PARAMETER_UPDATED",
  
  resource: {
    resource_type: "parameter",
    resource_id: "WEIGHT_CALC_001.compliance_weight"
  },
  
  change: {
    analyst: "analyst_a@cbp.gov",
    timestamp: "2026-06-12T10:30:00.123Z",
    old_value: 0.70,
    new_value: 0.75,
    reason: "Performance tuning - reduced false positives by 2%"
  },
  
  blockchain: {
    previous_event_hash: "abc123...",
    event_hash: "def456..."
  }
}
```

### 6.3 Implementation Steps

**Phase 1: Local Development (Week 1)**
1. Create SQLite schema for testing
   ```bash
   sqlite3 risk_scoring.db << 'EOF'
   CREATE TABLE rules (
     rule_id TEXT PRIMARY KEY,
     definition JSON,
     version INTEGER,
     updated_at DATETIME
   );
   
   CREATE TABLE audit_events (
     event_id TEXT PRIMARY KEY,
     rule_id TEXT,
     change JSON,
     timestamp DATETIME,
     analyst TEXT
   );
   EOF
   ```

2. Git-version rule YAML files
   ```
   rules/risk_scoring/weight_calculation.yaml
   rules/risk_scoring/compliance_check.yaml
   ```

**Phase 2: Firebase Setup (Week 1-2)**
1. Create Firestore database (Spark Plan = free)
   ```bash
   firebase init firestore
   ```

2. Deploy Firestore security rules
   ```javascript
   rules_version = '2';
   service cloud.firestore {
     match /databases/{database}/documents {
       // Analysts can update parameters
       match /rules_engine/parameters/{param_id} {
         allow read: if request.auth != null;
         allow create: if request.auth != null &&
                      request.resource.data.updated_by == request.auth.email;
         allow update: if request.auth != null &&
                      request.resource.data.updated_by == request.auth.email &&
                      resource.data.metadata.version == request.resource.data.metadata.version;
       }
       
       // Audit events are append-only
       match /rules_engine/audit_events/{event_id} {
         allow read: if request.auth != null;
         allow create: if request.auth != null;
         allow update, delete: if false;  // Never modify audit log
       }
     }
   }
   ```

3. Create TypeScript models
   ```typescript
   interface Parameter {
     param_id: string;
     value: number;
     metadata: {
       version: number;
       last_modified_by: string;
       last_modified_at: Date;
     };
   }
   
   interface AuditEvent {
     event_id: string;
     event_type: 'PARAMETER_UPDATED' | 'RULE_DEPLOYED';
     resource_id: string;
     change: {
       analyst: string;
       timestamp: Date;
       old_value: any;
       new_value: any;
       reason: string;
     };
   }
   ```

**Phase 3: Multi-Analyst UI (Week 2-3)**
1. Admin dashboard to update parameters
2. Optimistic concurrency handling
   ```typescript
   async function updateParameter(
     paramId: string,
     newValue: number,
     expectedVersion: number,
     analyst: string,
     reason: string
   ) {
     try {
       await db.runTransaction(async (transaction) => {
         const docRef = db.collection('rules_engine/parameters').doc(paramId);
         const docSnap = await transaction.get(docRef);
         
         if (docSnap.data().metadata.version !== expectedVersion) {
           throw new Error('Version mismatch - parameter was modified by another analyst');
         }
         
         transaction.update(docRef, {
           value: newValue,
           metadata: {
             version: expectedVersion + 1,
             last_modified_by: analyst,
             last_modified_at: new Date()
           }
         });
         
         // Create audit event
         transaction.set(
           db.collection('rules_engine/audit_events').doc(),
           {
             event_type: 'PARAMETER_UPDATED',
             resource_id: paramId,
             change: { analyst, new_value: newValue, reason, timestamp: new Date() }
           }
         );
       });
     } catch (error) {
       if (error.message.includes('Version mismatch')) {
         // Show UI: "Rule was updated by another analyst. Refresh and try again."
       }
     }
   }
   ```

3. Audit trail viewer
   ```typescript
   async function getParameterHistory(paramId: string) {
     const snapshot = await db
       .collection('rules_engine/audit_events')
       .where('resource_id', '==', paramId)
       .orderBy('change.timestamp', 'desc')
       .get();
     
     return snapshot.docs.map(doc => doc.data().change);
   }
   ```

**Phase 4: Temporal Queries & Compliance (Week 4)**
1. "As-of-date" historical state reconstruction
2. Compliance export (audit trail for CBP records)

### 6.4 Cost Breakdown (Annual)

| Component | Usage | Cost |
|-----------|-------|------|
| **Firestore** | 1000 shipments/day × 5 calls = 5K daily requests | $0 (free tier) |
| **Firestore Storage** | 1 GB parameters + 1.8 MB audit/year | $0 (free tier) |
| **Git (GitHub)** | Rules repository | $0 (public) or $4-12/month (private) |
| **Cloud Functions** (optional webhooks) | Parameter updates → cache invalidation | $0.40/million invocations (~$0.10/month) |
| **Total** | | **$0-12/year** |

---

## Part 7: Comparison Matrix

| Criterion | SQLite | MongoDB Community | RocksDB | Redis | Firestore | MongoDB Atlas | DynamoDB | Cosmos DB |
|-----------|--------|---|---|---|---|---|---|---|
| **Local Setup** | ✅ 0 min | ⚠️ 5 min | ⚠️ 5 min | ⚠️ 3 min | ❌ N/A | ❌ N/A | ❌ N/A | ❌ N/A |
| **Free Tier** | ✅ Unlimited | ✅ Community | ✅ Embedded | ❌ 30 MB | ✅ 1 GB | ✅ 0.5 GB | ✅ 25 GB | ✅ 25 GB |
| **Audit Logging** | ⚠️ Manual | ❌ Community | ❌ Manual | ❌ Manual | ✅ Append-only | ❌ No (M10+) | ⚠️ Streams | ✅ Append-only |
| **Scales 1000/day** | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes |
| **Multi-Analyst Safe** | ❌ Coarse locks | ✅ Optimistic | ❌ Single writer | ✅ Atomic ops | ✅ Optimistic | ✅ Optimistic | ✅ Conditional | ✅ ETag |
| **Version History** | ⚠️ Manual | ⚠️ Manual | ❌ Manual | ❌ Manual | ✅ Document + subcollection | ⚠️ Manual | ⚠️ Manual | ⚠️ Manual |
| **Temporal Queries** | ✅ SQL | ✅ Query API | ❌ Snapshot replay | ❌ AOF replay | ✅ Query API | ✅ Query API | ⚠️ DynamoDB Query | ✅ Query API |
| **Cost at Scale** | $0 | $0 | $0 | $7+/month | **$0** | $57+/month | $0 + S3 | **$0** |
| **Recommendation** | ✅ Local dev | ✅ Local dev | ⚠️ Embedded only | ❌ | **✅ Best** | ❌ Too expensive | ⚠️ Setup heavy | ✅ Also good |

---

## Conclusion

**For CBP Sentry Risk Scoring Rules Engine:**

1. **Local Development:** SQLite + Git-versioned rules YAML
   - Zero setup, file diffs are readable, commit history is audit trail
   - Run tests against SQLite, deploy rules to Firestore

2. **Production (Staging + Live):** Firebase Firestore
   - Free tier covers 1000s shipments/day indefinitely
   - Built-in optimistic concurrency for multi-analyst safety
   - Append-only audit events collection enables temporal queries
   - Real-time parameter updates (no code deploy needed)
   - Cost: $0 unless scaling beyond 50K reads/20K writes daily

3. **Rules Storage:** Git repository (YAML/JSON)
   - Quarterly releases (semantic versioning)
   - Code review before deployment
   - Full commit history = audit trail for rule changes

4. **Parameters Storage:** Firestore collection
   - Daily updates by analysts (real-time impact)
   - Version field prevents lost updates
   - Audit events track all changes (who, when, what, why)

5. **Multi-Analyst Pattern:** Optimistic concurrency control
   - Analyst B sees "conflict" if rule changed since fetch
   - Refetches and retries (simple + safe)
   - Alternative: Pessimistic lock for rule deployments (rare)

**Next Steps:**
1. Create Firestore database (Spark Plan)
2. Define rule/parameter data model (TypeScript interfaces)
3. Build analyst UI for parameter updates (with version check)
4. Implement audit trail queries (temporal, historical)
5. Set up CI/CD to deploy rules from Git → Firestore
6. Test multi-analyst concurrent edits

---

## References & Sources

- [MongoDB Atlas Free Tier Limits](https://www.mongodb.com/docs/atlas/reference/free-shared-limitations/)
- [Firebase Firestore Pricing](https://firebase.google.com/docs/firestore/pricing)
- [Google Cloud Firestore Pricing](https://cloud.google.com/firestore/pricing)
- [AWS DynamoDB Pricing](https://aws.amazon.com/dynamodb/pricing/)
- [Azure Cosmos DB Free Tier](https://learn.microsoft.com/en-us/azure/cosmos-db/free-tier)
- [SQLite JSON1 Documentation](https://sqlite.org/json1.html)
- [Redis Persistence Documentation](https://redis.io/docs/latest/operate/oss_and_stack/management/persistence/)
- [Rules Engine Design Patterns 2026](https://www.nected.ai/blog/rules-engine-design-pattern)
- [Event Sourcing & Audit Trails](https://www.techinterview.org/post/3233465463/system-design-event-sourcing/)
- [Optimistic Concurrency Control](https://binaryigor.com/optimistic-vs-pessimistic-locking.html)
- [Git as Database for Configuration](https://medium.com/agoda-engineering/how-we-transformed-payment-rule-management-with-git-as-a-database-f457818d5a1a)
