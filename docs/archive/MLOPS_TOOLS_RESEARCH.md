# MLOps Tools & Platforms Research

**Purpose:** Evaluate existing tools instead of building custom MLOps infrastructure

**Target Use Cases:**
- Model versioning & registry
- Data snapshot/delta management
- Approval workflows
- Model monitoring
- Experiment tracking
- Automated training pipelines

---

## 1. Model Registry & Version Control

### Option 1A: MLflow (Open Source, FREE)

**What it does:**
- Track experiments, parameters, metrics
- Store model artifacts (pkl, h5, onnx, etc.)
- Model registry with versioning
- Simple deployment

**Pros:**
- ✅ FREE, open source
- ✅ Works with any ML framework (XGBoost, TensorFlow, PyTorch)
- ✅ UI dashboard included
- ✅ Can run locally or on cloud
- ✅ Supports model stages (dev, staging, production)

**Cons:**
- ❌ No approval workflows built-in
- ❌ Limited monitoring (add separately)
- ❌ No data versioning

**Installation:**
```bash
pip install mlflow

# Start MLflow UI
mlflow ui  # http://localhost:5000
```

**Example - Register v3.0 Model:**
```python
import mlflow
from mlflow import log_model, log_params, log_metrics

# Log training run
with mlflow.start_run():
    # Log parameters
    mlflow.log_params({
        'model': 'xgboost',
        'n_estimators': 100,
        'max_depth': 6
    })
    
    # Log metrics
    mlflow.log_metrics({
        'accuracy': 0.92,
        'auc_roc': 0.94,
        'latency_ms': 85
    })
    
    # Register model
    mlflow.sklearn.log_model(model, 'cbp_risk_v3.0')

# Later: Load specific version
model = mlflow.pyfunc.load_model('models:/cbp-risk/production')
```

**Cost:** $0 (open source)

---

### Option 1B: Weights & Biases (Commercial, $19-99/month)

**What it does:**
- Experiment tracking
- Model versioning
- Hyperparameter optimization
- Model monitoring
- Team collaboration

**Pros:**
- ✅ Beautiful UI
- ✅ Real-time metrics streaming
- ✅ Built-in model monitoring
- ✅ Artifact storage (models, data)
- ✅ Integration with most frameworks
- ✅ Team collaboration features

**Cons:**
- ❌ Paid ($19+/month)
- ❌ Cloud-hosted (data leaves your control)
- ❌ Approval workflows not built-in

**Example:**
```python
import wandb

wandb.init(project='cbp-sentry', name='v3.0-training')

# Log metrics
wandb.log({
    'accuracy': 0.92,
    'auc_roc': 0.94,
    'latency_ms': 85,
    'model_version': 'v3.0'
})

# Log model artifact
wandb.save('models/xgboost_v3.0.pkl')
```

**Cost:** $19-99/month

---

### Option 1C: DVC (Data Version Control) + S3/GCS

**What it does:**
- Version control for data (not code)
- Model artifact versioning
- Pipeline orchestration
- Works with Git

**Pros:**
- ✅ FREE, open source
- ✅ Git-like workflow for data
- ✅ Works with GCP, AWS, Azure
- ✅ Stores large files in cloud, keeps metadata in Git
- ✅ No separate server needed

**Cons:**
- ❌ Steeper learning curve
- ❌ Different mindset than Git
- ❌ Limited UI (mostly CLI)
- ❌ No approval workflows

**Example - Track Model & Data:**
```bash
# Initialize DVC
dvc init

# Track data and model
dvc add models/xgboost_v3.0.pkl
dvc add data/training_data.csv

# Push to remote storage (GCS)
dvc remote add -d myremote gs://cbp-sentry-mlops
dvc push

# In Git
git add models/xgboost_v3.0.pkl.dvc
git commit -m "Add v3.0 model with DVC"
git tag v3.0-model

# Later: Restore exact version
git checkout v3.0-model
dvc pull  # Downloads model from GCS
```

**Cost:** $0 (open source)

---

## 2. Data Snapshot & Version Management

### Option 2A: Delta Lake (Open Source + Databricks)

**What it does:**
- ACID transactions on data lake
- Schema enforcement
- Time travel (restore to any point)
- Change data capture (CDCs)

**Pros:**
- ✅ Built for data versioning
- ✅ Restore to ANY timestamp
- ✅ Works with Spark, Python, SQL
- ✅ Open source with Databricks support
- ✅ Perfect for data snapshots!

**Cons:**
- ❌ Requires Spark infrastructure (complex setup)
- ❌ Overkill for small datasets initially
- ❌ Learning curve

**Perfect for:** Data snapshot use case (replaces our delta JSON approach)

**Example - Time Travel:**
```python
from delta.tables import DeltaTable

# Read current state
df = spark.read.format('delta').load('dbfs:/shipments')

# Restore to v2.1 state (2026-05-23)
df_v2_1 = spark.read.format('delta') \
    .option('timestampAsOf', '2026-05-23T14:00:00Z') \
    .load('dbfs:/shipments')

# View change history
history = DeltaTable.forPath(spark, 'dbfs:/shipments').history()
history.show()
```

**Cost:** $0 open source, or Databricks hosting ($0.40-2.00/DBU)

---

### Option 2B: Pachyderm (Open Source + Enterprise)

**What it does:**
- Data versioning (like Git for data)
- Pipeline orchestration
- Automatic data lineage
- Reproducibility

**Pros:**
- ✅ True Git for data
- ✅ Automatic lineage tracking
- ✅ Kubernetes-native
- ✅ Reproducible pipelines
- ✅ Open source

**Cons:**
- ❌ Requires Kubernetes (complex)
- ❌ Steeper operational overhead
- ❌ Not lightweight for small teams

**Cost:** $0 open source, or Pachyderm enterprise

---

## 3. MLOps Platforms (All-in-One)

### Option 3A: Kubeflow (Open Source)

**What it does:**
- Complete ML workflow orchestration
- Model serving
- Hyperparameter tuning
- Experiment tracking
- Pipeline management

**Pros:**
- ✅ FREE, open source
- ✅ Kubernetes-native
- ✅ Covers entire ML lifecycle
- ✅ Widely adopted in industry

**Cons:**
- ❌ Requires Kubernetes expertise
- ❌ Complex setup (30+ CRDs)
- ❌ Steep learning curve
- ❌ Overkill for small team

**Cost:** $0 open source, but requires Kubernetes

---

### Option 3B: Neptune.ai (Commercial, $99-499/month)

**What it does:**
- Experiment tracking
- Model registry
- Model monitoring
- Team collaboration
- Approval workflows (coming)

**Pros:**
- ✅ All-in-one platform
- ✅ Beautiful UI
- ✅ Real-time monitoring
- ✅ Good for teams
- ✅ Works with any framework

**Cons:**
- ❌ Paid ($99-499/month)
- ❌ Cloud-hosted
- ❌ Less customizable

**Cost:** $99-499/month

---

## 4. Data Snapshot Tools

### Option 4A: pg_partman (PostgreSQL Extension, FREE)

**For automated database snapshots:**

```sql
-- Create partition by date (enables incremental snapshots)
SELECT partman.create_parent(
    p_parent_table := 'public.shipments',
    p_control := 'created_at',
    p_type := 'range',
    p_interval := 'monthly'
);

-- Auto-create new partitions
SELECT partman.run_maintenance('public.shipments');

-- Old partitions easy to archive
-- New partitions easy to delete or backup separately
```

**Pros:**
- ✅ FREE (PostgreSQL native)
- ✅ Enables incremental backups
- ✅ Auto-manages old data
- ✅ Great for time-series data

---

### Option 4B: WAL-G (Backup Tool, FREE)

**For fast incremental PostgreSQL backups:**

```bash
# Install
pip install wal-g

# Take full backup
wal-g backup-push

# Restore to specific point-in-time
wal-g backup-fetch BACKUP_NAME

# Works with S3/GCS
export PGWAL_S3_BUCKET="cbp-sentry-backups"
export PGWAL_S3_PREFIX="postgres"
```

**Pros:**
- ✅ FREE, open source
- ✅ Incremental backups (92% storage reduction)
- ✅ Point-in-time recovery
- ✅ Works with any cloud storage

**Cost:** $0 (only pay for cloud storage)

---

## 5. Approval Workflow Tools

### Option 5A: Airflow (Open Source) + Custom Approval

**What it does:**
- DAG-based workflow orchestration
- Can add approval gates
- Email notifications
- Audit logging

**Example - Model Approval Gate:**
```python
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.models import Variable

with DAG('model_deployment_with_approval') as dag:
    
    train_model = PythonOperator(task_id='train', python_callable=train)
    
    # Approval gate (manual pause)
    approve_task = PythonOperator(
        task_id='await_approval',
        python_callable=send_approval_email
    )
    
    deploy_model = PythonOperator(task_id='deploy', python_callable=deploy)
    
    train_model >> approve_task >> deploy_model
```

**Pros:**
- ✅ FREE, open source
- ✅ Visual DAG monitoring
- ✅ Built-in approval gates
- ✅ Audit trail
- ✅ Runs locally or in cloud

**Cons:**
- ❌ Requires setup
- ❌ No UI for approval (uses email/Slack)

**Cost:** $0 open source

---

### Option 5B: GitHub Environments (FREE with GitHub)

**For approval workflows using GitHub Actions:**

```yaml
name: Deploy Model

on:
  push:
    branches: [main]

jobs:
  train:
    runs-on: ubuntu-latest
    outputs:
      model_version: ${{ steps.train.outputs.version }}
    steps:
      - run: python train_model.py
        id: train

  deploy_to_staging:
    runs-on: ubuntu-latest
    needs: train
    environment: staging  # Auto-notifies for approval
    steps:
      - run: python deploy.py ${{ needs.train.outputs.model_version }}

  deploy_to_production:
    runs-on: ubuntu-latest
    needs: [train, deploy_to_staging]
    environment: production  # Requires manual approval
    steps:
      - run: python deploy_prod.py ${{ needs.train.outputs.model_version }}
```

**Pros:**
- ✅ FREE (if using GitHub)
- ✅ Built-in approval UI
- ✅ Audit logging
- ✅ Integrates with GitHub

**Cons:**
- ❌ Limited to GitHub workflows
- ❌ Basic approval logic only

**Cost:** $0 (part of GitHub)

---

## 6. Model Monitoring & Observability

### Option 6A: Datadog (Commercial, $15-30+/month)

**What it does:**
- Real-time monitoring
- Metrics, logs, traces
- Anomaly detection
- Dashboards & alerts

**Pros:**
- ✅ Industry standard
- ✅ Easy setup
- ✅ Beautiful dashboards
- ✅ Anomaly detection

**Cons:**
- ❌ Paid ($15-30+/month)
- ❌ Can get expensive at scale

**Cost:** $15-30+/month

---

### Option 6B: Prometheus + Grafana (FREE)

**What it does:**
- Open source monitoring
- Custom metrics
- Alerting
- Dashboards

**Pros:**
- ✅ FREE, open source
- ✅ Run on-premises
- ✅ Highly customizable
- ✅ Industry standard

**Cons:**
- ❌ Requires setup
- ❌ Steeper learning curve

**Cost:** $0

---

## 7. Comparison Matrix

| Tool | Purpose | Cost | Setup | Approval | Data Versioning |
|---|---|---|---|---|---|
| **MLflow** | Model Registry | FREE | Easy | ❌ | ❌ |
| **Weights & Biases** | All-in-one | $19+/mo | Easy | ❌ | ❌ |
| **DVC** | Data Versioning | FREE | Medium | ❌ | ✅ |
| **Delta Lake** | Data Snapshots | FREE/$0.40+/DBU | Hard | ❌ | ✅✅ |
| **Pachyderm** | Pipelines | FREE | Hard | ❌ | ✅ |
| **Kubeflow** | ML Platform | FREE | Hard | ❌ | ❌ |
| **Neptune.ai** | All-in-one | $99+/mo | Easy | ❌ | ❌ |
| **Airflow** | Workflows | FREE | Medium | ✅ | ❌ |
| **GitHub Actions** | CI/CD | FREE | Easy | ✅ | ❌ |
| **Prometheus+Grafana** | Monitoring | FREE | Medium | ❌ | ❌ |
| **Datadog** | Monitoring | $15+/mo | Easy | ❌ | ❌ |

---

## 8. Recommended Stack for CBP Sentry

### **Approach 1: Lightweight (Recommended for NOW)**

```
┌─────────────────────────────────────────────────────┐
│         LIGHTWEIGHT MLOps STACK (FREE)               │
├─────────────────────────────────────────────────────┤
│                                                     │
│ Model Registry & Versioning:                        │
│ └─ MLflow (model artifact storage + versioning)    │
│    Cost: $0                                         │
│                                                     │
│ Data Snapshots & Deltas:                            │
│ └─ DVC + GCS (version data like code)              │
│    Cost: $0.023/GB/month (GCS standard tier)       │
│                                                     │
│ Approval Workflows:                                 │
│ └─ GitHub Actions Environments + Slack             │
│    Cost: $0 (part of GitHub)                       │
│                                                     │
│ Monitoring:                                         │
│ └─ Prometheus + Grafana (on-premises)              │
│    Cost: $0 (just infra)                           │
│                                                     │
│ TOTAL: $0 (software) + storage + infra costs       │
│                                                     │
└─────────────────────────────────────────────────────┘

Total Monthly Cost: ~$2-5 (GCS storage only)
Setup Time: 2-3 weeks
Team Size: 2-3 people
```

### **Approach 2: Enterprise (For Scale)**

```
┌─────────────────────────────────────────────────────┐
│         ENTERPRISE MLOps STACK (PAID)                │
├─────────────────────────────────────────────────────┤
│                                                     │
│ All-in-One Platform:                                │
│ └─ Weights & Biases                                │
│    ├─ Experiment tracking                          │
│    ├─ Model registry                               │
│    ├─ Monitoring                                   │
│    ├─ Team collaboration                           │
│    └─ Cost: $99/month (team plan)                  │
│                                                     │
│ Data Versioning:                                    │
│ └─ Delta Lake (if moving to Spark)                 │
│    Cost: Databricks $0.40-2/DBU                    │
│                                                     │
│ Approval Workflows:                                 │
│ └─ Airflow or GitHub Actions                       │
│    Cost: $0                                         │
│                                                     │
│ Monitoring:                                         │
│ └─ Datadog                                         │
│    Cost: $30/month                                 │
│                                                     │
│ TOTAL: ~$130-150/month                             │
│                                                     │
└─────────────────────────────────────────────────────┘

Total Monthly Cost: $130-150/month
Setup Time: 4-6 weeks
Team Size: 5+ people
```

---

## 9. Quick Implementation Plan

### **Phase 1: Add MLflow (This Week, 1 day)**

```python
# Location: services/risk-engine/training/mlflow_integration.py

import mlflow
from mlflow import log_model, log_params, log_metrics

async def train_and_register_model():
    """Train v3.0 and register in MLflow"""
    
    with mlflow.start_run():
        # Log parameters
        mlflow.log_params({
            'model_type': 'xgboost',
            'n_estimators': 100,
            'max_depth': 6,
            'learning_rate': 0.1
        })
        
        # Train model
        model = train_xgboost(X_train, y_train)
        
        # Log metrics
        metrics = evaluate_model(model, X_test, y_test)
        mlflow.log_metrics({
            'accuracy': metrics['accuracy'],
            'auc_roc': metrics['auc_roc'],
            'latency_ms': metrics['latency_ms']
        })
        
        # Register model
        mlflow.xgboost.log_model(
            model,
            'cbp-risk-v3.0',
            registered_model_name='cbp-risk'
        )
        
        # Tag the model version
        model_version = mlflow.register_model(
            'runs:/MODEL_RUN_ID/cbp-risk-v3.0',
            'cbp-risk'
        )
        
        mlflow.models.update_model_version(
            name='cbp-risk',
            version=model_version.version,
            description='XGBoost model with 3-gate architecture',
            tags={'domain': 'cbp', 'stage': 'staging'}
        )

# Later: Load specific version
def load_model_for_scoring(version='production'):
    model = mlflow.pyfunc.load_model(f'models:/cbp-risk/{version}')
    return model
```

**Setup:**
```bash
# Install
pip install mlflow xgboost

# Start MLflow UI
mlflow ui  # http://localhost:5000

# Access: http://localhost:5000/models
```

---

### **Phase 2: Add DVC for Data (Next Week, 2 days)**

```bash
# Initialize DVC
dvc init

# Configure remote storage (GCS)
dvc remote add -d myremote gs://cbp-sentry-mlops
dvc remote modify myremote projectname cbp-sentry

# Track data and models
dvc add data/training_data.csv
dvc add models/xgboost_v3.0.pkl

# Push to GCS
dvc push

# Git commit metadata
git add data/training_data.csv.dvc
git add models/xgboost_v3.0.pkl.dvc
git commit -m "Add v3.0 training data and model with DVC"
git tag v3.0-training-data
```

---

### **Phase 3: Add GitHub Environments (Following Week, 1 day)**

```yaml
# File: .github/workflows/deploy-model.yml

name: Deploy Model with Approval

on:
  push:
    branches: [main]

jobs:
  train:
    runs-on: ubuntu-latest
    outputs:
      model_version: ${{ steps.train.outputs.version }}
    steps:
      - uses: actions/checkout@v3
      - name: Train Model
        id: train
        run: python services/risk-engine/training/train_model.py
        
  approve_staging:
    runs-on: ubuntu-latest
    needs: train
    environment: 
      name: staging
      # Auto-notifies for approval
    steps:
      - name: Deploy to Staging
        run: ./scripts/deploy_model.sh ${{ needs.train.outputs.model_version }} staging

  approve_production:
    runs-on: ubuntu-latest
    needs: [train, approve_staging]
    environment:
      name: production
      # Requires manual approval from CODEOWNERS
    steps:
      - name: Deploy to Production
        run: ./scripts/deploy_model.sh ${{ needs.train.outputs.model_version }} production
```

---

## 10. Decision Matrix for CBP Sentry

**Question: Which tools should we implement?**

| Priority | Tool | Decision |
|---|---|---|
| **Phase 1 (NOW)** | MLflow | ✅ IMPLEMENT |
| | GitHub Actions | ✅ IMPLEMENT |
| | DVC | ✅ IMPLEMENT |
| **Phase 2 (Month 2)** | Prometheus+Grafana | ✅ IMPLEMENT |
| | Airflow | ⏳ CONSIDER IF workflows get complex |
| **Phase 3 (Month 3+)** | Weights & Biases | ⏳ IF team grows to 5+
| | Delta Lake | ⏳ IF moving to Spark |
| **Never** | Kubeflow | ❌ Overkill for current scale |

---

## 11. Total Cost Analysis (Year 1)

### **Lightweight Stack (Recommended)**
```
MLflow:              $0 (open source)
DVC:                 $0 (open source)
GCS Storage:         ~$30/month = $360/year
GitHub Actions:      $0 (free tier)
Prometheus+Grafana:  $0 (open source, server cost included)
──────────────────────────────────
TOTAL:               $360/year (+ server infrastructure)
```

### **Enterprise Stack**
```
Weights & Biases:    $99/month = $1,188/year
DVC:                 $0
Datadog:             $30/month = $360/year
GitHub Actions:      $0
──────────────────────────────────
TOTAL:               $1,548/year
```

---

## Next Steps

1. **This Week:** 
   - [ ] Install MLflow locally
   - [ ] Train v3.0 model with MLflow tracking
   - [ ] Verify model registry UI

2. **Next Week:**
   - [ ] Set up DVC with GCS
   - [ ] Version training data with DVC
   - [ ] Add DVC files to Git

3. **Following Week:**
   - [ ] Configure GitHub Environments for approval
   - [ ] Test approval workflow end-to-end
   - [ ] Add Prometheus metrics

4. **Month 2:**
   - [ ] Set up Prometheus + Grafana dashboards
   - [ ] Add model performance monitoring
   - [ ] Document MLOps workflow for team

---

## Research Conclusions

**Best practice for CBP Sentry:**

✅ **Use MLflow** — Industry standard, free, works with any framework
✅ **Use DVC** — Git-like data versioning, replaces our custom delta approach
✅ **Use GitHub Actions** — Free approval workflows, already familiar
✅ **Use Prometheus+Grafana** — Open source monitoring stack
❌ **Don't build custom** — These tools exist and are battle-tested

**Estimated effort:** 3-4 weeks to implement full MLOps with existing tools
**Cost:** $360-1,500/year (vs. $0 if custom-built, but custom would take 6+ weeks)

**ROI:** Better tooling + team familiarity + long-term maintainability >> building custom
