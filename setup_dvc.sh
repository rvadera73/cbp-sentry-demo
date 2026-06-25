#!/bin/bash
# DVC Setup Script for CBP Sentry
# Initializes DVC and versions training data and models

set -e

cd /home/rahulvadera/cbp-sentry

echo "📦 Phase 4: DVC (Data Version Control) Setup"
echo "=================================================================="

# 1. Initialize DVC
echo ""
echo "[1/5] Initializing DVC..."
if [ ! -d ".dvc" ]; then
    dvc init --no-scm
    echo "✅ DVC initialized"
else
    echo "⚠️  DVC already initialized"
fi

# 2. Configure local storage (for now)
echo ""
echo "[2/5] Configuring DVC storage..."
dvc remote add -d local /home/rahulvadera/cbp-sentry/dvc-storage 2>/dev/null || true
mkdir -p /home/rahulvadera/cbp-sentry/dvc-storage
echo "✅ Local storage configured: dvc-storage/"

# 3. Version training data
echo ""
echo "[3/5] Versioning training data..."
dvc add data/training_data.csv 2>/dev/null || echo "   (Already tracked)"
dvc add data/feature_matrix_72.csv 2>/dev/null || echo "   (Already tracked)"
echo "✅ Training data versioned"

# 4. Version models
echo ""
echo "[4/5] Versioning trained models..."
dvc add models/xgboost_model.json 2>/dev/null || echo "   (Already tracked)"
dvc add models/isolation_forest_model.pkl 2>/dev/null || echo "   (Already tracked)"
dvc add models/shap_explainer.pkl 2>/dev/null || echo "   (Already tracked)"
echo "✅ Models versioned"

# 5. Create DVC pipeline config
echo ""
echo "[5/5] Creating DVC pipeline..."
cat > dvc.yaml << 'EOFYAML'
stages:
  train:
    cmd: python3 train_models_phase1.py
    deps:
      - train_models_phase1.py
      - data/training_data.csv
      - data/feature_matrix_72.csv
    outs:
      - models/xgboost_model.json
      - models/isolation_forest_model.pkl
      - models/shap_explainer.pkl
    metrics:
      - test-results/phase1_training_results.json:
          cache: false
    plots:
      - test-results/phase1_detailed_metrics.json:
          x: model
          y: metrics
    params:
      - train_models_phase1.py:
          - XGBOOST_PARAMS
          - IFOREST_PARAMS

metrics:
  - test-results/phase1_training_results.json
EOFYAML
echo "✅ DVC pipeline created (dvc.yaml)"

echo ""
echo "=================================================================="
echo "✅ DVC Setup Complete!"
echo "=================================================================="
echo ""
echo "📊 DVC Workflow:"
echo "  1. Track changes: dvc add <file>"
echo "  2. Push to remote: dvc push"
echo "  3. Pull from remote: dvc pull"
echo "  4. Run pipeline: dvc repro"
echo "  5. View metrics: dvc plots show"
echo ""
echo "🔗 Next: Commit DVC files to Git"
echo "  git add data/training_data.csv.dvc data/feature_matrix_72.csv.dvc"
echo "  git add models/*.dvc dvc.yaml dvc.lock"
echo "  git commit -m 'Add DVC pipeline for model training and data versioning'"

