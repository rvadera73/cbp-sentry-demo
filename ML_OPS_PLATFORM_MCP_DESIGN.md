# ML Ops Platform as MCP Server

**Purpose:** Build a generic, reusable ML Operations Platform that works for ANY model + ANY dataset, exposed via MCP protocol

**Vision:** From "CBP Risk Model Service" → "Universal ML Ops Platform (MCP-enabled, Multi-tenant, Multi-model)"

---

## 1. Architecture: MCP Server + Generic ML Ops

### **High-Level Design**

```
┌────────────────────────────────────────────────────────┐
│                CBP SENTRY APPLICATION                  │
│  ┌─────────────────────────────────────────────────┐  │
│  │  Risk Model Management Tab (UI)                 │  │
│  │  └─ Consumes MCP: /model/versions, /metrics, etc
│  └─────────────────────────────────────────────────┘  │
└──────────────────┬─────────────────────────────────────┘
                   │ HTTP + MCP Protocol
                   ↓
┌────────────────────────────────────────────────────────┐
│         ML OPS PLATFORM (MCP Server)                   │
│                                                        │
│  ┌─ CORE: Generic Model Management Service            │
│  │  ├─ Models (any type: XGBoost, Neural Net, etc)   │
│  │  ├─ Datasets (any domain: CBP, FDA, etc)          │
│  │  ├─ Training Pipelines (flexible)                 │
│  │  ├─ Monitoring (universal metrics)                │
│  │  └─ Approvals (workflow engine)                   │
│  │                                                    │
│  ├─ MCP ENDPOINTS (for external AI/systems)          │
│  │  ├─ list_models                                   │
│  │  ├─ get_model_metrics                             │
│  │  ├─ explain_prediction                            │
│  │  ├─ detect_drift                                  │
│  │  ├─ trigger_training                              │
│  │  └─ approve_model                                 │
│  │                                                    │
│  ├─ REST API ENDPOINTS (for CBP Sentry)              │
│  │  ├─ /api/ml/models                                │
│  │  ├─ /api/ml/training/jobs                         │
│  │  ├─ /api/ml/metrics                               │
│  │  └─ /api/ml/predictions/{id}/explain              │
│  │                                                    │
│  └─ BACKGROUND JOBS (for all models)                 │
│     ├─ Model Training (pluggable)                    │
│     ├─ Drift Detection (pluggable)                   │
│     ├─ Performance Monitoring (pluggable)            │
│     └─ Retraining Triggers (pluggable)               │
│                                                        │
└────────────────────────────────────────────────────────┘
           ↑              ↑              ↑
           │              │              │
    ┌──────┴──┐    ┌──────┴──┐   ┌──────┴──┐
    │ Claude  │    │ Other   │   │ Internal│
    │ (via MCP)    │ AI Apps │   │ Systems │
    └──────────┘   └─────────┘   └─────────┘
```

---

## 2. Core Abstractions: Generic Model Service

Instead of "CBP Risk Model", design for **any model**:

```python
# Location: services/ml-ops-platform/core/models.py

from abc import ABC, abstractmethod
from typing import Any, Dict, List
from datetime import datetime

class MLModel(ABC):
    """Abstract base for any ML model"""
    
    @property
    @abstractmethod
    def model_id(self) -> str:
        """Unique identifier (e.g., 'cbp-risk-v3.0', 'fraud-detection-v2')"""
        pass
    
    @property
    @abstractmethod
    def domain(self) -> str:
        """Domain/tenant (e.g., 'cbp', 'fda', 'commerce')"""
        pass
    
    @property
    @abstractmethod
    def model_type(self) -> str:
        """Type (e.g., 'xgboost', 'neural_net', 'ensemble', 'llm')"""
        pass
    
    @abstractmethod
    async def predict(self, features: Dict[str, Any]) -> Dict[str, Any]:
        """
        Predict on input features
        
        Returns: {
            prediction: <model-specific>,
            confidence: 0.0-1.0,
            latency_ms: float,
            model_version: str,
            timestamp: datetime
        }
        """
        pass
    
    @abstractmethod
    async def explain_prediction(self, features: Dict[str, Any], prediction: Any) -> Dict[str, Any]:
        """
        Explain a prediction (SHAP, attention, saliency, etc)
        
        Returns: {
            feature_contributions: [{name, value, contribution}],
            top_features: [{}],
            confidence_interval: {lower, upper},
            explanation_type: str  # 'shap', 'attention', 'saliency', etc
        }
        """
        pass


class MLDataset(ABC):
    """Abstract base for any dataset"""
    
    @property
    @abstractmethod
    def dataset_id(self) -> str:
        """Unique identifier (e.g., 'cbp-shipments-2024', 'fraud-transactions-2024')"""
        pass
    
    @property
    @abstractmethod
    def domain(self) -> str:
        """Domain (e.g., 'cbp', 'fda', 'commerce')"""
        pass
    
    @property
    @abstractmethod
    def record_count(self) -> int:
        """Total records"""
        pass
    
    @property
    @abstractmethod
    def feature_count(self) -> int:
        """Total features"""
        pass
    
    @abstractmethod
    async def get_features_distribution(self) -> Dict[str, Any]:
        """
        Get feature distributions for drift detection
        
        Returns: {
            features: [{
                name: str,
                type: 'numeric' | 'categorical',
                mean: float,
                std: float,
                percentiles: {25, 50, 75},
                unique_count: int
            }]
        }
        """
        pass


class MLTrainingPipeline(ABC):
    """Abstract training pipeline - can be overridden per model"""
    
    @abstractmethod
    async def prepare_data(self, dataset: MLDataset) -> Dict[str, Any]:
        """Prepare training/test data"""
        pass
    
    @abstractmethod
    async def train(self, training_data: Dict) -> MLModel:
        """Train model on data"""
        pass
    
    @abstractmethod
    async def validate(self, model: MLModel, test_data: Dict) -> Dict[str, Any]:
        """Validate model performance"""
        pass
```

---

## 3. Multi-Tenant Data Schema

```sql
-- Generic model registry (works for any model)

CREATE TABLE ml_models (
    id TEXT PRIMARY KEY,
    model_id TEXT NOT NULL UNIQUE,  -- 'cbp-risk-v3.0'
    domain TEXT NOT NULL,            -- 'cbp', 'fda', 'commerce'
    model_type TEXT NOT NULL,        -- 'xgboost', 'neural_net', 'ensemble', 'llm'
    name TEXT NOT NULL,
    description TEXT,
    status TEXT,                     -- 'training', 'candidate', 'staging', 'production'
    version TEXT,
    framework TEXT,                  -- 'scikit-learn', 'xgboost', 'tensorflow', 'pytorch'
    artifact_path TEXT,              -- Location of model file
    feature_count INT,
    training_data_size INT,
    created_at DATETIME,
    created_by TEXT,
    approved_by TEXT,
    approved_at DATETIME,
    metadata JSON
);

CREATE TABLE ml_datasets (
    id TEXT PRIMARY KEY,
    dataset_id TEXT NOT NULL UNIQUE,  -- 'cbp-shipments-2024'
    domain TEXT NOT NULL,              -- 'cbp', 'fda', 'commerce'
    name TEXT NOT NULL,
    record_count INT,
    feature_count INT,
    time_period_start DATE,
    time_period_end DATE,
    data_location TEXT,               -- GCS path, S3 path, etc
    schema_definition JSON,           -- Feature definitions
    quality_score FLOAT,              -- Data quality 0-1
    created_at DATETIME
);

CREATE TABLE ml_training_jobs (
    id TEXT PRIMARY KEY,
    model_id TEXT,
    dataset_id TEXT,
    domain TEXT,
    status TEXT,                      -- 'queued', 'running', 'completed', 'failed'
    pipeline_type TEXT,               -- 'xgboost_pipeline', 'neural_net_pipeline', custom
    started_at DATETIME,
    completed_at DATETIME,
    metrics JSON,                     -- {accuracy, auc_roc, precision, recall, ...}
    hyperparameters JSON,
    validation_results JSON,
    artifacts_location TEXT,
    error_message TEXT,
    FOREIGN KEY (model_id) REFERENCES ml_models(id),
    FOREIGN KEY (dataset_id) REFERENCES ml_datasets(id)
);

CREATE TABLE ml_predictions (
    id TEXT PRIMARY KEY,
    model_id TEXT NOT NULL,
    domain TEXT NOT NULL,
    record_id TEXT,                   -- 'SHP-001', 'patient-123', etc
    features JSON,
    prediction ANY,                   -- Model-specific
    confidence FLOAT,
    latency_ms INT,
    explanation JSON,                 -- SHAP/attention values
    created_at DATETIME,
    FOREIGN KEY (model_id) REFERENCES ml_models(id)
);

CREATE TABLE ml_metrics (
    id TEXT PRIMARY KEY,
    model_id TEXT NOT NULL,
    domain TEXT NOT NULL,
    metric_name TEXT,                 -- 'accuracy', 'auc_roc', 'latency', etc
    metric_value FLOAT,
    segment TEXT,                     -- Optional: 'origin_country=CN', 'patient_age=65+', etc
    timestamp DATETIME,
    FOREIGN KEY (model_id) REFERENCES ml_models(id)
);

CREATE TABLE ml_drift_detected (
    id TEXT PRIMARY KEY,
    model_id TEXT,
    dataset_id TEXT,
    domain TEXT,
    drift_type TEXT,                  -- 'data_drift', 'model_drift', 'prediction_drift'
    feature_name TEXT,
    drift_score FLOAT,
    detected_at DATETIME,
    status TEXT,                      -- 'new', 'acknowledged', 'resolved'
    action_taken TEXT
);

CREATE TABLE ml_approvals (
    id TEXT PRIMARY KEY,
    model_id TEXT NOT NULL,
    domain TEXT NOT NULL,
    requested_by TEXT,
    requested_at DATETIME,
    approvers JSON,                   -- [{user, vote, comment, voted_at}]
    status TEXT,                      -- 'pending', 'approved', 'rejected'
    approval_stage TEXT,              -- 'staging', 'production'
    FOREIGN KEY (model_id) REFERENCES ml_models(id)
);
```

---

## 4. MCP Server Interface

### **What is MCP?**

MCP (Model Context Protocol) is a standard protocol for exposing tools/resources to Claude and other AI systems.

**Benefits:**
- Claude can directly access ML ops platform
- Other AI apps can use same interface
- Standard, documented protocol
- Can be consumed by any system supporting MCP

### **MCP Resources (Exposed)**

```
MCP Resources:
├─ models://model/{model_id}
│  └─ GET model details, metrics, status
│
├─ models://model/{model_id}/metrics
│  └─ GET performance metrics (accuracy, latency, etc)
│
├─ models://model/{model_id}/predictions/{record_id}
│  └─ GET prediction + explanation for a record
│
├─ datasets://dataset/{dataset_id}
│  └─ GET dataset information, schema, quality
│
├─ datasets://dataset/{dataset_id}/drift
│  └─ GET drift status and feature distributions
│
├─ jobs://training/{job_id}
│  └─ GET training job status and results
│
└─ approvals://pending
   └─ GET pending approval queue
```

### **MCP Tools (Functions)**

```
MCP Tools:
├─ list_models(domain: str = None)
│  └─ List all models, optionally filtered by domain
│
├─ get_model_metrics(model_id: str, time_range: str = "7d")
│  └─ Get model metrics over time
│
├─ explain_prediction(model_id: str, record_id: str)
│  └─ Get SHAP/explanation for a specific prediction
│
├─ detect_drift(model_id: str, dataset_id: str)
│  └─ Trigger drift detection job
│
├─ trigger_training(domain: str, model_type: str, dataset_id: str)
│  └─ Queue training job for new model
│
├─ approve_model(model_id: str, approver: str, vote: str)
│  └─ Vote on model approval
│
├─ compare_models(model_id_1: str, model_id_2: str, dataset_id: str)
│  └─ Compare two models on same dataset
│
└─ get_monitoring_status(domain: str, model_id: str = None)
   └─ Get current health/monitoring status
```

---

## 5. Concrete Implementations for Different Models

### **Example 1: CBP Risk Model (XGBoost)**

```python
# Location: services/ml-ops-platform/models/cbp_risk_model.py

from core.models import MLModel, MLDataset, MLTrainingPipeline
import xgboost as xgb
import shap

class CBPRiskModel(MLModel):
    """CBP risk scoring model (XGBoost)"""
    
    @property
    def model_id(self) -> str:
        return "cbp-risk-v3.0"
    
    @property
    def domain(self) -> str:
        return "cbp"
    
    @property
    def model_type(self) -> str:
        return "xgboost"
    
    async def predict(self, features: Dict[str, Any]) -> Dict[str, Any]:
        # XGBoost specific prediction
        risk_score = self.xgb_model.predict(features)[0]
        return {
            'prediction': risk_score,
            'confidence': self.calculate_confidence(risk_score),
            'latency_ms': 85,
            'model_version': 'v3.0'
        }
    
    async def explain_prediction(self, features, prediction) -> Dict[str, Any]:
        # SHAP for XGBoost
        shap_values = self.explainer.shap_values(features)
        return {
            'feature_contributions': shap_values,
            'top_features': sorted by importance,
            'explanation_type': 'shap'
        }


class CBPRiskDataset(MLDataset):
    """CBP shipments dataset"""
    
    @property
    def dataset_id(self) -> str:
        return "cbp-shipments-2024"
    
    @property
    def domain(self) -> str:
        return "cbp"


class CBPRiskTrainingPipeline(MLTrainingPipeline):
    """XGBoost training pipeline for CBP risk model"""
    
    async def train(self, training_data: Dict) -> MLModel:
        # XGBoost-specific training
        dtrain = xgb.DMatrix(training_data['X'], training_data['y'])
        model = xgb.train(params={...}, dtrain=dtrain)
        return CBPRiskModel(model)
```

### **Example 2: FDA Drug Adverse Event Model (Neural Network)**

```python
# Location: services/ml-ops-platform/models/fda_adverse_event_model.py

from core.models import MLModel, MLDataset, MLTrainingPipeline
import tensorflow as tf

class FDAAdverseEventModel(MLModel):
    """FDA adverse event classifier (Neural Network)"""
    
    @property
    def model_id(self) -> str:
        return "fda-adverse-event-v1.0"
    
    @property
    def domain(self) -> str:
        return "fda"
    
    @property
    def model_type(self) -> str:
        return "neural_net"
    
    async def predict(self, features: Dict[str, Any]) -> Dict[str, Any]:
        # Neural network specific prediction
        prediction = self.neural_net.predict(features)[0]
        return {
            'prediction': prediction,
            'confidence': prediction[0],  # softmax output
            'latency_ms': 120,
            'model_version': 'v1.0'
        }
    
    async def explain_prediction(self, features, prediction) -> Dict[str, Any]:
        # Attention weights for neural net
        attention = self.get_attention_weights(features)
        return {
            'feature_contributions': attention,
            'explanation_type': 'attention'
        }


class FDAAdverseEventDataset(MLDataset):
    """FDA adverse event reports dataset"""
    
    @property
    def dataset_id(self) -> str:
        return "fda-reports-2024"
    
    @property
    def domain(self) -> str:
        return "fda"


class FDATrainingPipeline(MLTrainingPipeline):
    """TensorFlow training pipeline for FDA model"""
    
    async def train(self, training_data: Dict) -> MLModel:
        # Neural net-specific training
        model = tf.keras.Sequential([...])
        model.fit(training_data['X'], training_data['y'])
        return FDAAdverseEventModel(model)
```

### **Example 3: Commerce Fraud Detection (LLM)**

```python
# Location: services/ml-ops-platform/models/commerce_fraud_model.py

from core.models import MLModel, MLDataset, MLTrainingPipeline
import anthropic

class CommerceFraudModel(MLModel):
    """Commerce fraud detection using Claude (LLM)"""
    
    @property
    def model_id(self) -> str:
        return "commerce-fraud-v2.0"
    
    @property
    def domain(self) -> str:
        return "commerce"
    
    @property
    def model_type(self) -> str:
        return "llm"
    
    async def predict(self, features: Dict[str, Any]) -> Dict[str, Any]:
        # LLM-based prediction (using Claude)
        prompt = self.build_fraud_detection_prompt(features)
        response = await self.client.messages.create(
            model="claude-opus-4-1",
            messages=[{"role": "user", "content": prompt}]
        )
        fraud_score = self.parse_llm_response(response)
        return {
            'prediction': fraud_score,
            'confidence': 0.95,  # LLM confidence
            'latency_ms': 450,
            'model_version': 'v2.0'
        }
    
    async def explain_prediction(self, features, prediction) -> Dict[str, Any]:
        # LLM generates its own explanation
        explanation_prompt = self.build_explanation_prompt(features)
        response = await self.client.messages.create(...)
        return {
            'explanation': response.content[0].text,
            'explanation_type': 'llm_reasoning'
        }
```

---

## 6. MCP Server Implementation

```python
# Location: services/ml-ops-platform/mcp_server.py

from mcp.server import Server
from mcp.types import Resource, Tool
import json

class MLOpsMCPServer:
    """MCP Server for ML Operations Platform"""
    
    def __init__(self):
        self.server = Server("ml-ops-platform")
        self.register_resources()
        self.register_tools()
    
    def register_resources(self):
        """Register MCP resources"""
        
        @self.server.list_resources()
        async def list_resources():
            # List all available models, datasets, jobs
            models = await self.db.query("SELECT * FROM ml_models")
            datasets = await self.db.query("SELECT * FROM ml_datasets")
            
            return [
                Resource(
                    uri=f"models://model/{m['model_id']}",
                    name=m['name'],
                    mimeType="application/json"
                )
                for m in models
            ] + [
                Resource(
                    uri=f"datasets://dataset/{d['dataset_id']}",
                    name=d['name'],
                    mimeType="application/json"
                )
                for d in datasets
            ]
        
        @self.server.read_resource()
        async def read_resource(uri: str):
            # Read resource by URI
            if uri.startswith("models://model/"):
                model_id = uri.split("/")[-1]
                model = await self.get_model(model_id)
                metrics = await self.get_model_metrics(model_id)
                return json.dumps({
                    'model': model,
                    'metrics': metrics
                })
            # ... more resource types
    
    def register_tools(self):
        """Register MCP tools (functions)"""
        
        @self.server.call_tool()
        async def handle_tool_call(name: str, arguments: dict):
            if name == "list_models":
                domain = arguments.get("domain")
                return await self.list_models(domain)
            
            elif name == "explain_prediction":
                model_id = arguments["model_id"]
                record_id = arguments["record_id"]
                return await self.explain_prediction(model_id, record_id)
            
            elif name == "trigger_training":
                domain = arguments["domain"]
                model_type = arguments["model_type"]
                dataset_id = arguments["dataset_id"]
                return await self.trigger_training(domain, model_type, dataset_id)
            
            # ... more tools
    
    async def start(self):
        """Start MCP server"""
        async with self.server:
            pass  # MCP server now running
```

---

## 7. Usage Examples

### **From Claude (via MCP)**

```
User: "Compare CBP risk model v3.0 vs v3.1"

Claude gets resources:
- models://model/cbp-risk-v3.0
- models://model/cbp-risk-v3.1

Claude calls tools:
- compare_models("cbp-risk-v3.0", "cbp-risk-v3.1", "cbp-shipments-2024")
- Returns: {accuracy_diff: +1.1%, latency_diff: -5ms, ...}

Claude responds: "v3.1 is more accurate (+1.1%) and faster..."
```

### **From CBP Sentry UI (via REST API)**

```python
# Calls the same backend
response = await fetch('/api/ml/models/cbp-risk-v3.0/metrics')
# Gets: {accuracy: 0.92, auc_roc: 0.94, latency_ms: 85}

response = await fetch('/api/ml/predictions/SHP-001/explain')
# Gets: {shap_values: {...}, top_features: [...]}
```

### **From External AI/System (via MCP)**

```javascript
// Another AI system connects to MCP server
const mlops = new MCPClient('ml-ops-platform')

// List all models
const models = await mlops.callTool('list_models', {domain: 'fda'})

// Explain a prediction
const explanation = await mlops.callTool('explain_prediction', {
  model_id: 'fda-adverse-event-v1.0',
  record_id: 'report-12345'
})
```

---

## 8. Architecture Benefits

```
BEFORE (Single-purpose):
ML Ops Platform
└─ CBP Risk Model only
   ├─ Training (XGBoost-specific)
   ├─ Monitoring (CBP-specific metrics)
   └─ Approval (CBP-specific workflow)

AFTER (Multi-tenant, Multi-model, MCP-exposed):
ML Ops Platform (MCP Server)
├─ Generic Core
│  ├─ Model Registry (any type)
│  ├─ Dataset Management (any domain)
│  ├─ Training Pipeline (pluggable)
│  ├─ Monitoring (universal)
│  └─ Approval Engine (generic)
│
├─ Model Implementations
│  ├─ CBP Risk Model (XGBoost)
│  ├─ FDA Adverse Event (Neural Net)
│  ├─ Commerce Fraud (LLM)
│  └─ Custom Model (user-defined)
│
├─ Exposure
│  ├─ MCP Resources (for Claude/AI systems)
│  ├─ MCP Tools (for Claude/AI systems)
│  ├─ REST API (for CBP Sentry UI)
│  └─ Internal APIs (for background jobs)
│
└─ Multi-Tenant Support
   ├─ Domain isolation (cbp, fda, commerce, ...)
   ├─ Dataset versioning per domain
   ├─ Model versioning per domain
   └─ Approval workflows per domain
```

---

## 9. Implementation Roadmap

### **Phase 1: Core Abstractions (Weeks 1-2)**
```
- Define MLModel, MLDataset, MLTrainingPipeline base classes
- Create multi-tenant database schema
- Build model registry system
```

### **Phase 2: MCP Server (Weeks 2-3)**
```
- Implement MCP resources
- Implement MCP tools
- Integrate with model registry
```

### **Phase 3: CBP Implementation (Weeks 3-4)**
```
- Implement CBPRiskModel (inherits from MLModel)
- Implement CBPRiskDataset (inherits from MLDataset)
- Implement CBPRiskTrainingPipeline (inherits from MLTrainingPipeline)
```

### **Phase 4: REST API + UI (Weeks 4-5)**
```
- Build REST endpoints (/api/ml/...)
- Build Risk Model Management tab (uses REST API)
- Connect to MCP server for SHAP/monitoring
```

### **Phase 5: Extensibility (Weeks 5-6)**
```
- Add FDA model support
- Add Custom model template
- Document how to add new models
```

---

## 10. How Other Systems Use It

### **Claude Direct (via MCP)**
```
User: "Help me understand the drift in CBP risk model"

Claude:
1. Calls list_models() → finds cbp-risk-v3.0
2. Calls detect_drift(cbp-risk-v3.0) → gets drift report
3. Reads resource models://model/cbp-risk-v3.0/drift
4. Explains: "Feature X distribution changed 3% ..."
```

### **FDA Analysis System**
```
System connects to MCP server
Calls: list_models(domain='fda')
Gets all FDA models available
Calls: explain_prediction('fda-adverse-event-v1.0', 'report-123')
Returns explanation for integration into FDA system
```

### **CBP Sentry UI (via REST API)**
```
React component calls:
GET /api/ml/models/cbp-risk-v3.0/metrics
GET /api/ml/predictions/SHP-001/explain
POST /api/ml/training/jobs

Tab shows:
- Model versions
- Metrics dashboard
- Per-shipment explanations
- Approval queue
```

### **Automated Retraining (Background Job)**
```
Background job calls:
POST /api/ml/training/jobs/trigger
  {domain: 'cbp', dataset_id: 'cbp-shipments-2024'}

Trains new model
Validates
Creates as candidate
Posts to approval queue
```

---

## 11. Multi-Model Example: 3 Domains

```
ML Ops Platform (Single Instance)
│
├─ DOMAIN: CBP
│  ├─ Model: cbp-risk-v3.0 (XGBoost, PRODUCTION)
│  ├─ Model: cbp-risk-v3.1 (XGBoost, STAGING)
│  ├─ Dataset: cbp-shipments-2024 (150M records)
│  └─ Metrics: accuracy, latency, fairness by origin
│
├─ DOMAIN: FDA
│  ├─ Model: fda-adverse-event-v1.0 (Neural Net, PRODUCTION)
│  ├─ Model: fda-adverse-event-v1.1 (Neural Net, CANDIDATE)
│  ├─ Dataset: fda-reports-2024 (10M records)
│  └─ Metrics: precision, recall, fairness by drug class
│
└─ DOMAIN: COMMERCE
   ├─ Model: commerce-fraud-v2.0 (LLM, PRODUCTION)
   ├─ Model: commerce-fraud-v2.1 (LLM, STAGING)
   ├─ Dataset: commerce-transactions-2024 (500M records)
   └─ Metrics: fraud detection rate, false positive rate

MCP Resources expose:
- models://model/cbp-risk-v3.0
- models://model/fda-adverse-event-v1.0
- models://model/commerce-fraud-v2.0
- datasets://dataset/cbp-shipments-2024
- datasets://dataset/fda-reports-2024
- datasets://dataset/commerce-transactions-2024

Claude can query across all domains:
"Which domain's model has the highest drift this week?"
"Compare explainability across all three models"
"Which domain needs retraining?"
```

---

## Summary: From Single-Purpose to Universal Platform

| Aspect | Before | After |
|---|---|---|
| **Models** | CBP risk only | Any model type |
| **Datasets** | CBP shipments only | Any domain/dataset |
| **Training** | XGBoost-specific | Pluggable pipelines |
| **Exposure** | Internal REST API only | MCP + REST + internal APIs |
| **Users** | CBP Sentry UI only | Claude + CBP Sentry + External AI systems |
| **Multi-tenant** | Single domain (CBP) | Multiple domains (CBP, FDA, Commerce, ...) |
| **Extensibility** | Hard-coded for CBP | Template-based for new models/domains |
| **Reusability** | 0% (CBP-specific code) | 100% (generic core + pluggable implementations) |

**This becomes a platform, not an application.**
