"""Firestore database client and initialization"""

from firebase_admin import credentials, firestore, initialize_app
import logging
from typing import Optional

logger = logging.getLogger(__name__)

_firestore_client: Optional[firestore.client.AsyncClient] = None

async def init_firestore():
    """Initialize Firestore client"""
    global _firestore_client
    try:
        # In demo mode, use environment variable or service account key
        # In production, Cloud Run has automatic credentials via Workload Identity
        _firestore_client = firestore.client()
        logger.info("Firestore client initialized")
    except Exception as e:
        logger.error(f"Failed to initialize Firestore: {e}")
        raise

def get_firestore_client() -> firestore.client.Client:
    """Get the Firestore client instance"""
    if _firestore_client is None:
        raise RuntimeError("Firestore not initialized. Call init_firestore() first.")
    return _firestore_client

async def create_collections_if_not_exist():
    """Create necessary Firestore collections with schema documentation"""
    db = get_firestore_client()

    collections_schema = {
        "corridors": {
            "doc_example": "corridors/760410_VN_US",
            "fields": ["hts_6", "origin", "destination", "risk_level", "ad_cvd_cases"]
        },
        "shipments": {
            "doc_example": "shipments/{bill_id}",
            "fields": ["bill_id", "manifest_id", "shipper", "consignee", "h1_intelligence", "h2_intelligence", "h3_score"]
        },
        "referral_packages": {
            "doc_example": "referral_packages/{package_id}",
            "fields": ["package_id", "shipment_id", "score", "confidence_level", "sections"]
        },
        "entity_resolutions": {
            "doc_example": "entity_resolutions/{entity_id}",
            "fields": ["entity_id", "name", "type", "jurisdiction", "senzing_id", "resolved_entities"]
        }
    }

    logger.info("Firestore collections initialized (collections created on first write)")
    return collections_schema
