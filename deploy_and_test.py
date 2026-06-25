#!/usr/bin/env python3
"""
Deploy risk-engine microservice and run integration tests.

This script:
1. Builds the Docker image for risk-engine
2. Starts the container locally
3. Runs integration tests
4. Uploads models to GCP (optional)
5. Validates deployment
"""
import os
import sys
import subprocess
import json
import time
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
RISK_ENGINE_DIR = Path("/home/rahulvadera/cbp-sentry/services/risk-engine")
MODELS_DIR = Path("/home/rahulvadera/cbp-sentry/models")
RESULTS_DIR = Path("/home/rahulvadera/cbp-sentry/test-results")
DOCKER_IMAGE = os.getenv("DOCKER_IMAGE", "cbp-sentry-risk-engine:latest")
DOCKER_REGISTRY = os.getenv("DOCKER_REGISTRY", "gcr.io/cbp-sentry-ml")
CONTAINER_NAME = "risk-engine-test"
CONTAINER_PORT = 8004
HOST_PORT = 8004
DEPLOYMENT_TIMEOUT = 300  # 5 minutes


def run_command(cmd: str, cwd: Path = None, timeout: int = 120) -> tuple:
    """
    Run a shell command and return output.

    Args:
        cmd: Command to run
        cwd: Working directory
        timeout: Command timeout in seconds

    Returns:
        Tuple of (return_code, stdout, stderr)
    """
    logger.info(f"Running: {cmd}")
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return 1, "", f"Command timeout after {timeout}s"
    except Exception as e:
        return 1, "", str(e)


def build_docker_image() -> bool:
    """
    Build Docker image for risk-engine.

    Returns:
        Success flag
    """
    print("\n[1/6] Building Docker Image")
    print("-" * 80)

    cmd = f"docker build -t {DOCKER_IMAGE} ."
    returncode, stdout, stderr = run_command(cmd, cwd=RISK_ENGINE_DIR)

    if returncode == 0:
        logger.info(f"Docker image built: {DOCKER_IMAGE}")
        return True
    else:
        logger.error(f"Docker build failed")
        logger.error(f"STDERR: {stderr}")
        return False


def start_container() -> bool:
    """
    Start risk-engine container.

    Returns:
        Success flag
    """
    print("\n[2/6] Starting Container")
    print("-" * 80)

    # Stop existing container if running
    stop_cmd = f"docker stop {CONTAINER_NAME} 2>/dev/null || true"
    run_command(stop_cmd)

    # Remove existing container
    rm_cmd = f"docker rm {CONTAINER_NAME} 2>/dev/null || true"
    run_command(rm_cmd)

    # Start new container
    start_cmd = f"""docker run -d \
        --name {CONTAINER_NAME} \
        -p {HOST_PORT}:{CONTAINER_PORT} \
        -e FLASK_ENV=development \
        -e PORT={CONTAINER_PORT} \
        -v {MODELS_DIR}:/app/models:ro \
        -e ML_MODELS_DIR=/app/models \
        {DOCKER_IMAGE}"""

    returncode, stdout, stderr = run_command(start_cmd)

    if returncode == 0:
        logger.info(f"Container started: {CONTAINER_NAME}")

        # Wait for container to be healthy
        print("Waiting for container to be healthy...")
        for attempt in range(30):
            health_cmd = f"docker inspect -f '{{{{.State.Health.Status}}}}' {CONTAINER_NAME}"
            returncode, stdout, _ = run_command(health_cmd)

            if returncode == 0 and "healthy" in stdout:
                logger.info(f"Container is healthy (attempt {attempt + 1})")
                return True

            time.sleep(1)

        logger.warning("Container started but health check not confirmed, proceeding with tests")
        return True
    else:
        logger.error(f"Failed to start container")
        logger.error(f"STDERR: {stderr}")
        return False


def run_integration_tests() -> Dict[str, Any]:
    """
    Run integration tests against the service.

    Returns:
        Test results dictionary
    """
    print("\n[3/6] Running Integration Tests")
    print("-" * 80)

    cmd = f"python {RISK_ENGINE_DIR}/test_integration.py"
    returncode, stdout, stderr = run_command(cmd, timeout=120)

    logger.info("Integration test output:")
    print(stdout)

    if returncode != 0:
        logger.error(f"Integration tests failed")
        if stderr:
            logger.error(f"STDERR: {stderr}")

    # Try to load results JSON
    results_file = RESULTS_DIR / "integration_test_results.json"
    if results_file.exists():
        try:
            with open(results_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Could not load test results: {e}")

    return {"success": returncode == 0}


def check_model_performance() -> Dict[str, Any]:
    """
    Check model performance metrics.

    Returns:
        Performance metrics
    """
    print("\n[4/6] Checking Model Performance")
    print("-" * 80)

    metrics_file = RESULTS_DIR / "phase1_detailed_metrics.json"
    if metrics_file.exists():
        try:
            with open(metrics_file, 'r') as f:
                metrics = json.load(f)

            auc = metrics.get("xgboost", {}).get("auc", 0)
            logger.info(f"XGBoost AUC: {auc:.4f}")

            if auc >= 0.82:
                logger.info("AUC meets threshold (>= 0.82)")
                return {"auc": auc, "meets_threshold": True}
            else:
                logger.warning(f"AUC below threshold: {auc:.4f} < 0.82")
                return {"auc": auc, "meets_threshold": False}

        except Exception as e:
            logger.warning(f"Could not load metrics: {e}")

    return {"auc": 0, "meets_threshold": False}


def upload_to_gcp() -> bool:
    """
    Upload models to GCP (optional).

    Returns:
        Success flag
    """
    print("\n[5/6] Uploading to GCP (Optional)")
    print("-" * 80)

    # Check if GCP credentials are available
    if not os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
        logger.info("GCP credentials not configured, skipping upload")
        return False

    cmd = f"python {RISK_ENGINE_DIR}/gcp_uploader.py"
    returncode, stdout, stderr = run_command(cmd, timeout=180)

    logger.info("GCP upload output:")
    print(stdout)

    return returncode == 0


def cleanup_container():
    """Stop and remove test container."""
    logger.info("Cleaning up container...")
    stop_cmd = f"docker stop {CONTAINER_NAME} 2>/dev/null || true"
    run_command(stop_cmd)
    rm_cmd = f"docker rm {CONTAINER_NAME} 2>/dev/null || true"
    run_command(rm_cmd)


def main():
    """Main deployment and test pipeline."""
    print("=" * 80)
    print("RISK-ENGINE MICROSERVICE DEPLOYMENT & TESTING")
    print("=" * 80)
    print(f"Risk Engine Dir: {RISK_ENGINE_DIR}")
    print(f"Models Dir: {MODELS_DIR}")
    print(f"Docker Image: {DOCKER_IMAGE}")
    print(f"Container: {CONTAINER_NAME}")

    start_time = time.time()
    results = {
        "timestamp": datetime.now().isoformat(),
        "docker_image": DOCKER_IMAGE,
        "container_name": CONTAINER_NAME,
        "stages": {}
    }

    try:
        # Stage 1: Build image
        if not build_docker_image():
            logger.error("Docker build failed")
            results["stages"]["docker_build"] = False
            return results

        results["stages"]["docker_build"] = True

        # Stage 2: Start container
        if not start_container():
            logger.error("Container startup failed")
            results["stages"]["container_start"] = False
            return results

        results["stages"]["container_start"] = True

        # Stage 3: Run integration tests
        test_results = run_integration_tests()
        results["stages"]["integration_tests"] = test_results.get("success", False)
        results["test_details"] = test_results

        # Stage 4: Check model performance
        metrics = check_model_performance()
        results["stages"]["performance_check"] = metrics.get("meets_threshold", False)
        results["auc"] = metrics.get("auc", 0)

        # Stage 5: Upload to GCP
        gcp_success = upload_to_gcp()
        results["stages"]["gcp_upload"] = gcp_success

    finally:
        # Cleanup
        cleanup_container()

    # Calculate timing
    total_time = time.time() - start_time
    results["deployment_time_minutes"] = total_time / 60

    # Summary
    print("\n" + "=" * 80)
    print("DEPLOYMENT SUMMARY")
    print("=" * 80)

    for stage, success in results["stages"].items():
        status = "PASS" if success else "FAIL"
        print(f"{stage:30s}: {status}")

    print(f"\nTotal deployment time: {results['deployment_time_minutes']:.2f} minutes")
    print(f"AUC: {results['auc']:.4f}")

    # Save results
    RESULTS_DIR.mkdir(exist_ok=True)
    results_file = RESULTS_DIR / "deployment_results.json"
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)

    logger.info(f"Results saved to {results_file}")

    overall_success = all(results["stages"].values())
    return 0 if overall_success else 1


if __name__ == "__main__":
    sys.exit(main())
