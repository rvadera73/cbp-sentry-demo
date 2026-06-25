"""Test fixtures module for CBP Sentry"""

import json
from pathlib import Path
from typing import List, Dict, Any

FIXTURES_DIR = Path(__file__).parent


def load_shipments() -> List[Dict[str, Any]]:
    """Load sample shipments from fixture file"""
    fixture_path = FIXTURES_DIR / "shipments.json"
    if fixture_path.exists():
        with open(fixture_path, 'r') as f:
            return json.load(f)
    return []


def load_shap_responses() -> List[Dict[str, Any]]:
    """Load sample SHAP responses from fixture file"""
    fixture_path = FIXTURES_DIR / "shap_responses.json"
    if fixture_path.exists():
        with open(fixture_path, 'r') as f:
            return json.load(f)
    return []


def get_sample_shipment(shipment_id: str = "SHP-000001") -> Dict[str, Any]:
    """Get a specific sample shipment"""
    shipments = load_shipments()
    for shipment in shipments:
        if shipment['id'] == shipment_id:
            return shipment
    return shipments[0] if shipments else {}


def get_sample_shap_response(shipment_id: str = "SHP-000001") -> Dict[str, Any]:
    """Get SHAP response for a specific shipment"""
    responses = load_shap_responses()
    for response in responses:
        if response['shipment_id'] == shipment_id:
            return response
    return responses[0] if responses else {}


__all__ = [
    'load_shipments',
    'load_shap_responses',
    'get_sample_shipment',
    'get_sample_shap_response',
]
