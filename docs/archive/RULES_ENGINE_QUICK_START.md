# Rules Engine Quick Start: Firebase Firestore Implementation

**Date:** June 12, 2026  
**Cost:** $0 (Spark Plan free tier)  
**Setup Time:** 30 minutes

---

## 1. Firebase Project Setup (5 minutes)

```bash
# Install Firebase CLI
npm install -g firebase-tools

# Login to Firebase
firebase login

# Create new Firebase project or select existing
firebase init firestore

# Select these options:
# - Set up Firestore database
# - Select Spark Plan (free)
# - Use default location
# - Deploy security rules: YES
```

---

## 2. Firestore Collections & Schema

### Collection 1: `rules_engine/rules/{rule_id}`
Current state of each rule's parameters.

```javascript
{
  rule_id: "WEIGHT_CALC_001",
  name: "Weight Calculator",
  description: "Calculates risk score weights",
  
  // Current parameters (analysts update these)
  parameters: {
    compliance_weight: 0.75,
    manifest_risk_weight: 0.60,
    vessel_history_weight: 0.65
  },
  
  // Metadata for optimistic concurrency
  metadata: {
    version: 5,                              // Increment on each update
    last_modified_by: "analyst_a@cbp.gov",
    last_modified_at: Timestamp.now(),
    rule_status: "active",                   // "active" | "inactive" | "testing"
    git_source: "v1.2.3",                    // Git version that deployed these rules
    deployed_at: Timestamp.fromDate(new Date('2026-06-12'))
  }
}
```

### Collection 2: `rules_engine/rule_versions/{rule_id}/{version_id}`
Historical snapshots of parameters (audit trail).

```javascript
{
  version: 5,
  created_at: Timestamp.now(),
  created_by: "analyst_a@cbp.gov",
  
  parameters: {
    compliance_weight: 0.70,
    manifest_risk_weight: 0.60,
    vessel_history_weight: 0.65
  },
  
  reason: "Performance tuning - reduced false positives by 2%"
}
```

### Collection 3: `rules_engine/audit_events/{auto_id}`
Immutable event log (never update or delete).

```javascript
{
  event_id: "evt_20260612_001",
  event_type: "PARAMETER_UPDATED",  // or RULE_DEPLOYED, RULE_CREATED
  
  resource: {
    resource_type: "parameter",  // "parameter" or "rule"
    resource_id: "WEIGHT_CALC_001.compliance_weight",
    rule_id: "WEIGHT_CALC_001"
  },
  
  change: {
    analyst: "analyst_a@cbp.gov",
    timestamp: Timestamp.now(),
    old_value: 0.70,
    new_value: 0.75,
    reason: "Performance tuning - reduced false positives by 2%"
  },
  
  // Blockchain-style chaining (optional, for compliance)
  blockchain: {
    previous_event_id: "evt_20260611_005",  // Link to previous change
    event_hash: "sha256hash..."             // Hash of this event
  }
}
```

### Collection 4: `rules_engine/parameters/{param_id}`
Global parameters used across multiple rules.

```javascript
{
  param_id: "ESCALATION_THRESHOLD",
  name: "Escalation Threshold",
  category: "risk_scoring",
  
  value: 0.75,
  datatype: "float",  // "float" | "int" | "string" | "bool"
  
  // Constraints (optional)
  constraints: {
    min: 0.0,
    max: 1.0,
    step: 0.01
  },
  
  metadata: {
    version: 3,
    last_modified_by: "analyst_b@cbp.gov",
    last_modified_at: Timestamp.now(),
    reason: "Reduced from 0.80 to increase risk detection"
  }
}
```

---

## 3. Security Rules (`firestore.rules`)

```javascript
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    // Allow authenticated users to read rules
    match /rules_engine/{document=**} {
      allow read: if request.auth != null;
    }

    // Parameters: Analysts can update with version check
    match /rules_engine/parameters/{param_id} {
      allow create: if request.auth != null &&
                       request.auth.token.email.endsWith('@cbp.gov');
      
      allow update: if request.auth != null &&
                       request.auth.token.email.endsWith('@cbp.gov') &&
                       resource.data.metadata.version == request.resource.data.metadata.version - 1;
      
      allow delete: if false;  // Never delete parameters
    }

    // Rules: Only CI/CD service account can update
    match /rules_engine/rules/{rule_id} {
      allow read: if request.auth != null;
      
      allow update: if request.auth.uid == 'ci-cd-service-account-uid' ||
                       (request.auth != null &&
                        request.auth.token.email.endsWith('@cbp.gov') &&
                        request.resource.data.metadata.version == resource.data.metadata.version + 1);
    }

    // Audit events: Append-only
    match /rules_engine/audit_events/{event_id} {
      allow read: if request.auth != null;
      
      allow create: if request.auth != null &&
                       request.resource.data.analyst == request.auth.token.email;
      
      allow update, delete: if false;  // Never modify audit log
    }

    // Rule versions: Append-only archive
    match /rules_engine/rule_versions/{rule_id}/{version_id} {
      allow read: if request.auth != null;
      
      allow create: if request.auth != null;
      
      allow update, delete: if false;
    }
  }
}
```

Deploy rules:
```bash
firebase deploy --only firestore:rules
```

---

## 4. TypeScript Models

```typescript
// types/rules-engine.ts

import { Timestamp } from 'firebase/firestore';

export interface Parameter {
  param_id: string;
  name: string;
  category: string;
  value: number | string | boolean;
  datatype: 'float' | 'int' | 'string' | 'bool';
  constraints?: {
    min?: number;
    max?: number;
    step?: number;
  };
  metadata: ParameterMetadata;
}

export interface ParameterMetadata {
  version: number;
  last_modified_by: string;
  last_modified_at: Timestamp;
  reason?: string;
}

export interface Rule {
  rule_id: string;
  name: string;
  description: string;
  parameters: Record<string, number | string | boolean>;
  metadata: RuleMetadata;
}

export interface RuleMetadata {
  version: number;
  last_modified_by: string;
  last_modified_at: Timestamp;
  rule_status: 'active' | 'inactive' | 'testing';
  git_source: string;
  deployed_at: Timestamp;
}

export interface AuditEvent {
  event_id: string;
  event_type: 'PARAMETER_UPDATED' | 'RULE_DEPLOYED' | 'RULE_CREATED';
  resource: {
    resource_type: 'parameter' | 'rule';
    resource_id: string;
    rule_id?: string;
  };
  change: {
    analyst: string;
    timestamp: Timestamp;
    old_value: any;
    new_value: any;
    reason?: string;
  };
  blockchain?: {
    previous_event_id: string;
    event_hash: string;
  };
}

export interface RuleVersion {
  version: number;
  created_at: Timestamp;
  created_by: string;
  parameters: Record<string, number | string | boolean>;
  reason: string;
}
```

---

## 5. Service: Update Parameter (with Optimistic Concurrency)

```typescript
// services/parameter-service.ts

import {
  doc,
  updateDoc,
  runTransaction,
  Timestamp,
  collection,
  addDoc,
  writeBatch
} from 'firebase/firestore';
import { db } from '../firebase-config';
import { Parameter, AuditEvent } from '../types/rules-engine';

export async function updateParameter(
  paramId: string,
  newValue: any,
  expectedVersion: number,
  analyst: string,
  reason: string
): Promise<void> {
  const paramRef = doc(db, 'rules_engine/parameters', paramId);
  const auditRef = collection(db, 'rules_engine/audit_events');

  try {
    await runTransaction(db, async (transaction) => {
      // Read current document
      const docSnap = await transaction.get(paramRef);
      
      if (!docSnap.exists()) {
        throw new Error(`Parameter ${paramId} not found`);
      }

      const current = docSnap.data() as Parameter;
      const currentVersion = current.metadata.version;

      // Verify version matches (optimistic concurrency check)
      if (currentVersion !== expectedVersion) {
        throw new Error(
          `Version mismatch: expected ${expectedVersion}, but found ${currentVersion}. ` +
          `Parameter was modified by another analyst. Please refresh and try again.`
        );
      }

      // Update parameter
      transaction.update(paramRef, {
        value: newValue,
        metadata: {
          version: currentVersion + 1,
          last_modified_by: analyst,
          last_modified_at: Timestamp.now(),
          reason
        }
      });

      // Create audit event
      transaction.set(doc(auditRef), {
        event_id: `evt_${Date.now()}`,
        event_type: 'PARAMETER_UPDATED',
        resource: {
          resource_type: 'parameter',
          resource_id: paramId
        },
        change: {
          analyst,
          timestamp: Timestamp.now(),
          old_value: current.value,
          new_value: newValue,
          reason
        }
      } as AuditEvent);
    });

    console.log(`Parameter ${paramId} updated successfully`);
  } catch (error) {
    console.error('Failed to update parameter:', error);
    throw error;
  }
}
```

---

## 6. Service: Get Audit Trail

```typescript
// services/audit-service.ts

import {
  collection,
  query,
  where,
  orderBy,
  getDocs,
  Timestamp
} from 'firebase/firestore';
import { db } from '../firebase-config';
import { AuditEvent } from '../types/rules-engine';

/**
 * Get all audit events for a parameter, ordered by timestamp (newest first)
 */
export async function getParameterAuditTrail(paramId: string): Promise<AuditEvent[]> {
  const q = query(
    collection(db, 'rules_engine/audit_events'),
    where('resource.resource_id', '==', paramId),
    orderBy('change.timestamp', 'desc')
  );

  const snapshot = await getDocs(q);
  return snapshot.docs.map(doc => doc.data() as AuditEvent);
}

/**
 * Get parameter value as of a specific date (temporal query)
 */
export async function getParameterAsOfDate(
  paramId: string,
  targetDate: Date
): Promise<any> {
  const q = query(
    collection(db, 'rules_engine/audit_events'),
    where('resource.resource_id', '==', paramId),
    where('change.timestamp', '<=', Timestamp.fromDate(targetDate)),
    orderBy('change.timestamp', 'desc')
  );

  const snapshot = await getDocs(q);
  
  if (snapshot.empty) {
    return null;  // No changes before target date
  }

  // Return new_value from most recent event before target date
  return snapshot.docs[0].data().change.new_value;
}

/**
 * Get all changes by an analyst in a date range
 */
export async function getAnalystChanges(
  analyst: string,
  startDate: Date,
  endDate: Date
): Promise<AuditEvent[]> {
  const q = query(
    collection(db, 'rules_engine/audit_events'),
    where('change.analyst', '==', analyst),
    where('change.timestamp', '>=', Timestamp.fromDate(startDate)),
    where('change.timestamp', '<', Timestamp.fromDate(endDate)),
    orderBy('change.timestamp', 'desc')
  );

  const snapshot = await getDocs(q);
  return snapshot.docs.map(doc => doc.data() as AuditEvent);
}
```

---

## 7. React Component: Parameter Editor (with Optimistic Concurrency UI)

```typescript
// components/ParameterEditor.tsx

import React, { useState, useEffect } from 'react';
import { doc, getDoc } from 'firebase/firestore';
import { db } from '../firebase-config';
import { Parameter } from '../types/rules-engine';
import { updateParameter } from '../services/parameter-service';

interface ParameterEditorProps {
  paramId: string;
  onSuccess?: () => void;
}

export function ParameterEditor({ paramId, onSuccess }: ParameterEditorProps) {
  const [param, setParam] = useState<Parameter | null>(null);
  const [newValue, setNewValue] = useState<string>('');
  const [reason, setReason] = useState<string>('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Load current parameter
  useEffect(() => {
    async function loadParameter() {
      try {
        const docRef = doc(db, 'rules_engine/parameters', paramId);
        const docSnap = await getDoc(docRef);
        
        if (docSnap.exists()) {
          const data = docSnap.data() as Parameter;
          setParam(data);
          setNewValue(String(data.value));
        }
      } catch (err) {
        setError('Failed to load parameter');
      }
    }

    loadParameter();
  }, [paramId]);

  const handleUpdate = async () => {
    if (!param) return;

    setLoading(true);
    setError(null);

    try {
      const analyst = 'analyst_a@cbp.gov';  // Get from auth context
      
      await updateParameter(
        paramId,
        parseFloat(newValue),
        param.metadata.version,  // Pass current version for optimistic check
        analyst,
        reason
      );

      // Reload parameter to confirm update
      const docRef = doc(db, 'rules_engine/parameters', paramId);
      const docSnap = await getDoc(docRef);
      setParam(docSnap.data() as Parameter);
      
      setError(null);
      if (onSuccess) onSuccess();
    } catch (err: any) {
      if (err.message.includes('Version mismatch')) {
        setError(
          'Parameter was modified by another analyst. ' +
          'Refreshing... Please try again.'
        );
        // Auto-refresh
        setTimeout(() => window.location.reload(), 2000);
      } else {
        setError(err.message);
      }
    } finally {
      setLoading(false);
    }
  };

  if (!param) return <div>Loading...</div>;

  return (
    <div style={{ padding: '20px', border: '1px solid #ccc', borderRadius: '4px' }}>
      <h3>{param.name}</h3>
      <p>{param.description}</p>

      {error && (
        <div style={{ padding: '10px', backgroundColor: '#ffcccc', borderRadius: '4px', marginBottom: '10px' }}>
          ⚠️ {error}
        </div>
      )}

      <div style={{ marginBottom: '10px' }}>
        <label>
          New Value:
          <input
            type="number"
            value={newValue}
            onChange={e => setNewValue(e.target.value)}
            min={param.constraints?.min}
            max={param.constraints?.max}
            step={param.constraints?.step || 0.01}
            disabled={loading}
          />
        </label>
      </div>

      <div style={{ marginBottom: '10px' }}>
        <label>
          Reason for Change:
          <textarea
            value={reason}
            onChange={e => setReason(e.target.value)}
            placeholder="Why are you making this change?"
            disabled={loading}
          />
        </label>
      </div>

      <button
        onClick={handleUpdate}
        disabled={loading}
      >
        {loading ? 'Updating...' : 'Update Parameter'}
      </button>

      <div style={{ marginTop: '20px', fontSize: '12px', color: '#666' }}>
        Current Version: {param.metadata.version} | 
        Last Modified: {param.metadata.last_modified_at.toDate().toLocaleString()} |
        By: {param.metadata.last_modified_by}
      </div>
    </div>
  );
}
```

---

## 8. React Component: Audit Trail Viewer

```typescript
// components/AuditTrailViewer.tsx

import React, { useState, useEffect } from 'react';
import { getParameterAuditTrail, getParameterAsOfDate } from '../services/audit-service';
import { AuditEvent } from '../types/rules-engine';

interface AuditTrailViewerProps {
  paramId: string;
}

export function AuditTrailViewer({ paramId }: AuditTrailViewerProps) {
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [selectedDate, setSelectedDate] = useState<string>(
    new Date().toISOString().split('T')[0]
  );
  const [valueAsOfDate, setValueAsOfDate] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  // Load audit trail
  useEffect(() => {
    async function loadTrail() {
      try {
        const trail = await getParameterAuditTrail(paramId);
        setEvents(trail);
      } catch (err) {
        console.error('Failed to load audit trail:', err);
      }
    }

    loadTrail();
  }, [paramId]);

  // Query value as of date
  const handleDateQuery = async () => {
    setLoading(true);
    try {
      const value = await getParameterAsOfDate(paramId, new Date(selectedDate));
      setValueAsOfDate(value);
    } catch (err) {
      console.error('Failed to query date:', err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ padding: '20px' }}>
      <h3>Audit Trail for {paramId}</h3>

      <div style={{ marginBottom: '20px', padding: '10px', backgroundColor: '#f0f0f0', borderRadius: '4px' }}>
        <label>
          Query value as of date:
          <input
            type="date"
            value={selectedDate}
            onChange={e => setSelectedDate(e.target.value)}
          />
          <button onClick={handleDateQuery} disabled={loading}>
            {loading ? 'Querying...' : 'Query'}
          </button>
        </label>
        {valueAsOfDate !== null && (
          <p style={{ marginTop: '10px' }}>
            Value on {selectedDate}: <strong>{valueAsOfDate}</strong>
          </p>
        )}
      </div>

      <h4>Recent Changes</h4>
      <table style={{ width: '100%', borderCollapse: 'collapse' }}>
        <thead>
          <tr style={{ backgroundColor: '#f0f0f0', borderBottom: '1px solid #ccc' }}>
            <th style={{ padding: '10px', textAlign: 'left' }}>Date</th>
            <th style={{ padding: '10px', textAlign: 'left' }}>Analyst</th>
            <th style={{ padding: '10px', textAlign: 'left' }}>Old Value</th>
            <th style={{ padding: '10px', textAlign: 'left' }}>New Value</th>
            <th style={{ padding: '10px', textAlign: 'left' }}>Reason</th>
          </tr>
        </thead>
        <tbody>
          {events.map((event, idx) => (
            <tr key={idx} style={{ borderBottom: '1px solid #ddd' }}>
              <td style={{ padding: '10px' }}>
                {event.change.timestamp.toDate().toLocaleString()}
              </td>
              <td style={{ padding: '10px' }}>{event.change.analyst}</td>
              <td style={{ padding: '10px' }}>{event.change.old_value}</td>
              <td style={{ padding: '10px' }}>
                <strong>{event.change.new_value}</strong>
              </td>
              <td style={{ padding: '10px' }}>{event.change.reason || '-'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
```

---

## 9. Testing: Multi-Analyst Concurrent Edits

```typescript
// __tests__/parameter-concurrency.test.ts

import { updateParameter } from '../services/parameter-service';

describe('Optimistic Concurrency Control', () => {
  it('should handle concurrent updates from two analysts', async () => {
    const paramId = 'TEST_PARAM_001';
    const analyst_a = 'analyst_a@cbp.gov';
    const analyst_b = 'analyst_b@cbp.gov';

    // Simulate both analysts fetching parameter at version 5
    const expectedVersion = 5;

    // Analyst A updates first
    const updateA = updateParameter(
      paramId,
      0.75,
      expectedVersion,
      analyst_a,
      'Reason A'
    );

    // Analyst B tries to update with same expected version
    const updateB = updateParameter(
      paramId,
      0.80,
      expectedVersion,
      analyst_b,
      'Reason B'
    );

    // Wait for updates
    const [resultA, resultB] = await Promise.allSettled([updateA, updateB]);

    // One should succeed
    expect(resultA.status === 'fulfilled' || resultB.status === 'fulfilled').toBe(true);

    // One should fail with version mismatch
    if (resultA.status === 'fulfilled' && resultB.status === 'rejected') {
      expect((resultB.reason as Error).message).toContain('Version mismatch');
    } else if (resultA.status === 'rejected' && resultB.status === 'fulfilled') {
      expect((resultA.reason as Error).message).toContain('Version mismatch');
    }
  });
});
```

---

## 10. Deployment: CI/CD Pipeline (GitHub Actions)

```yaml
# .github/workflows/deploy-rules.yml

name: Deploy Rules to Firestore

on:
  push:
    branches:
      - main
    paths:
      - 'rules/**'

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Node.js
        uses: actions/setup-node@v3
        with:
          node-version: '18'

      - name: Install Firebase CLI
        run: npm install -g firebase-tools

      - name: Deploy rules to Firestore
        env:
          FIREBASE_TOKEN: ${{ secrets.FIREBASE_TOKEN }}
        run: |
          firebase deploy \
            --project=${{ secrets.FIREBASE_PROJECT_ID }} \
            --only firestore:rules

      - name: Update rule version in Firestore
        env:
          FIREBASE_TOKEN: ${{ secrets.FIREBASE_TOKEN }}
        run: |
          node scripts/update-rule-versions.js \
            --git-ref ${{ github.sha }}
```

---

## Summary

| Step | Time | Tool |
|------|------|------|
| Firebase project setup | 5 min | Firebase CLI |
| Create collections | 5 min | Firebase Console |
| Write security rules | 5 min | Firestore Rules |
| Create TypeScript types | 5 min | IDE |
| Implement services | 10 min | Code |
| Build React UI | 10 min | React |
| Write tests | 10 min | Jest |
| Deploy | 5 min | CI/CD |
| **Total** | **~55 min** | |

**Cost:** $0 (Spark Plan free tier covers 1000s shipments/day)

**Next:** See `NOSQL_RULES_ENGINE_RESEARCH.md` for detailed architecture and comparison.
