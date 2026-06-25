#!/usr/bin/env python3
"""Upload trained models to GCP Cloud Storage."""
import os
import sys
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

try:
    from google.cloud import storage
except ImportError:
    print("ERROR: google-cloud-storage not installed")
    sys.exit(1)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
MODELS_DIR = Path("/home/rahulvadera/cbp-sentry/models")
GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID", "cbp-sentry-ml")
GCP_BUCKET = os.getenv("GCP_MODELS_BUCKET", "cbp-sentry-models")
MODEL_VERSION = os.getenv("MODEL_VERSION", "phase1-v1")


def upload_models_to_gcp() -> Dict[str, Any]:
    """
    Upload trained models to GCP Cloud Storage.

    Returns:
        Upload results dictionary
    """
    print("=" * 80)
    print("UPLOADING MODELS TO GCP CLOUD STORAGE")
    print("=" * 80)
    print(f"Project ID: {GCP_PROJECT_ID}")
    print(f"Bucket: {GCP_BUCKET}")
    print(f"Model Version: {MODEL_VERSION}")
    print(f"Models Directory: {MODELS_DIR}")

    results = {
        "timestamp": datetime.now().isoformat(),
        "project_id": GCP_PROJECT_ID,
        "bucket": GCP_BUCKET,
        "model_version": MODEL_VERSION,
        "files_uploaded": [],
        "errors": [],
        "success": False
    }

    try:
        # Initialize GCS client
        storage_client = storage.Client(project=GCP_PROJECT_ID)

        # Check if bucket exists
        try:
            bucket = storage_client.get_bucket(GCP_BUCKET)
            logger.info(f"Bucket {GCP_BUCKET} found")
        except Exception as e:
            logger.error(f"Bucket {GCP_BUCKET} not found: {e}")
            results["errors"].append(f"Bucket not found: {e}")
            return results

        # Model files to upload
        model_files = [
            "xgboost_model.json",
            "isolation_forest_model.pkl",
            "shap_explainer.pkl",
            "shap_values_sample.npy",
            "scaler.pkl"
        ]

        # Upload each model file
        for filename in model_files:
            local_path = MODELS_DIR / filename
            if not local_path.exists():
                logger.warning(f"File not found: {local_path}")
                results["errors"].append(f"File not found: {filename}")
                continue

            try:
                # Create GCS blob path
                gcs_path = f"models/{MODEL_VERSION}/{filename}"
                blob = bucket.blob(gcs_path)

                # Upload file
                logger.info(f"Uploading {filename} to gs://{GCP_BUCKET}/{gcs_path}")
                blob.upload_from_filename(str(local_path))

                # Get file size
                file_size = local_path.stat().st_size
                results["files_uploaded"].append({
                    "filename": filename,
                    "gcs_path": f"gs://{GCP_BUCKET}/{gcs_path}",
                    "size_bytes": file_size
                })

                logger.info(f"Uploaded {filename} ({file_size} bytes)")

            except Exception as e:
                error_msg = f"Error uploading {filename}: {e}"
                logger.error(error_msg)
                results["errors"].append(error_msg)

        # Create manifest file
        try:
            manifest = {
                "version": MODEL_VERSION,
                "timestamp": datetime.now().isoformat(),
                "models": {
                    "xgboost": {
                        "filename": "xgboost_model.json",
                        "type": "json",
                        "description": "XGBoost classifier for illegal transshipment detection"
                    },
                    "isolation_forest": {
                        "filename": "isolation_forest_model.pkl",
                        "type": "pickle",
                        "description": "Isolation Forest for anomaly detection"
                    },
                    "shap_explainer": {
                        "filename": "shap_explainer.pkl",
                        "type": "pickle",
                        "description": "SHAP TreeExplainer for model interpretability"
                    },
                    "scaler": {
                        "filename": "scaler.pkl",
                        "type": "pickle",
                        "description": "Feature scaler"
                    }
                },
                "features": 72,
                "training_samples": 7201,
                "test_samples": 3086
            }

            manifest_path = f"models/{MODEL_VERSION}/manifest.json"
            manifest_blob = bucket.blob(manifest_path)
            manifest_blob.upload_from_string(
                json.dumps(manifest, indent=2),
                content_type="application/json"
            )

            logger.info(f"Uploaded manifest to gs://{GCP_BUCKET}/{manifest_path}")
            results["manifest_path"] = f"gs://{GCP_BUCKET}/{manifest_path}"

        except Exception as e:
            logger.error(f"Error uploading manifest: {e}")
            results["errors"].append(f"Manifest upload failed: {e}")

        # Determine success
        if len(results["files_uploaded"]) >= 3:  # At least XGBoost, IF, SHAP
            results["success"] = True
            logger.info(f"Successfully uploaded {len(results['files_uploaded'])} files")
        else:
            logger.error("Not enough files uploaded")

        return results

    except Exception as e:
        error_msg = f"Fatal error: {e}"
        logger.error(error_msg)
        results["errors"].append(error_msg)
        return results


def main():
    """Main upload process."""
    results = upload_models_to_gcp()

    # Print results
    print("\n" + "=" * 80)
    print("UPLOAD RESULTS")
    print("=" * 80)
    print(f"Success: {results['success']}")
    print(f"Files uploaded: {len(results['files_uploaded'])}")

    for file_info in results["files_uploaded"]:
        print(f"  - {file_info['filename']}: {file_info['size_bytes']} bytes")

    if results["errors"]:
        print(f"\nErrors ({len(results['errors'])}):")
        for error in results["errors"]:
            print(f"  - {error}")

    # Save results to JSON
    output_path = Path("/home/rahulvadera/cbp-sentry/test-results/gcp_upload_results.json")
    output_path.parent.mkdir(exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"\nResults saved to: {output_path}")

    return 0 if results["success"] else 1


if __name__ == "__main__":
    sys.exit(main())
