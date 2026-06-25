"""
Pytest configuration and fixtures for CBP Sentry risk model tests.

Provides async database sessions, test data, mock services, and API clients
for unit and integration testing.
"""

import pytest
import asyncio
import os
import json
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta
from typing import AsyncGenerator, Dict, Any, Optional
from unittest.mock import Mock, AsyncMock, MagicMock

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

# Configuration
TEST_DB_PATH = Path("/tmp/test_cbp_sentry.db")
TEST_DB_URL = f"sqlite:///{TEST_DB_PATH}"
FIXTURES_DIR = Path(__file__).parent / "fixtures"


# ============================================================================
# EVENT LOOP & ASYNC SETUP
# ============================================================================

@pytest.fixture(scope="session")
def event_loop_policy():
    """Set event loop policy for tests"""
    policy = asyncio.get_event_loop_policy()
    return policy


@pytest.fixture(scope="session")
def event_loop(event_loop_policy):
    """Create event loop for async tests"""
    loop = event_loop_policy.new_event_loop()
    yield loop
    loop.close()


# ============================================================================
# DATABASE FIXTURES
# ============================================================================

@pytest.fixture(scope="function")
async def db_session() -> AsyncGenerator[Session, None]:
    """
    Create a temporary SQLite database session with test data.

    Yields a SQLAlchemy session with:
    - Fresh database schema
    - Seeded model versions, shipments, risk scores
    - Automatic cleanup on test completion
    """
    # Clean up existing test DB
    if TEST_DB_PATH.exists():
        TEST_DB_PATH.unlink()

    # Create connection and schema
    conn = sqlite3.connect(str(TEST_DB_PATH))
    cursor = conn.cursor()

    # Create tables
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS model_versions (
            id TEXT PRIMARY KEY,
            model_name TEXT NOT NULL,
            version_number TEXT NOT NULL,
            training_date DATETIME,
            released_at DATETIME,
            is_active BOOLEAN DEFAULT 0,
            deprecated_at DATETIME,
            total_calculations INTEGER,
            notes TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS risk_scores_cache (
            id TEXT PRIMARY KEY,
            shipment_id TEXT NOT NULL,
            current_model_version TEXT,
            final_score FLOAT,
            risk_breakdown TEXT,
            confidence_interval TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS shipments (
            id TEXT PRIMARY KEY,
            manifest_id TEXT,
            origin_country TEXT,
            destination_country TEXT,
            hs_code TEXT,
            declared_value_usd FLOAT,
            declared_weight_kg FLOAT,
            shipper_name TEXT,
            consignee_name TEXT,
            status TEXT DEFAULT 'received',
            calculated_risk_score FLOAT,
            risk_score_breakdown TEXT,
            confidence_interval TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME
        )
    """)

    # Seed test data
    now = datetime.utcnow()

    # Model versions
    cursor.execute("""
        INSERT INTO model_versions VALUES
        ('v3.0', 'CBP Risk v3.0', 'v3.0', ?, ?, 1, NULL, 15432, 'Active production'),
        ('v3.1', 'CBP Risk v3.1', 'v3.1', ?, NULL, 0, NULL, 0, 'Candidate'),
        ('v2.1', 'CBP Risk v2.1', 'v2.1', ?, ?, 0, ?, 5000, 'Deprecated')
    """, (
        now - timedelta(days=2),
        now - timedelta(hours=12),
        now - timedelta(days=30),
        now - timedelta(days=30),
        now - timedelta(hours=12)
    ))

    # Risk score cache
    for i in range(100):
        cursor.execute("""
            INSERT INTO risk_scores_cache VALUES
            (?, ?, 'v3.0', ?, ?, ?, ?)
        """, (
            f"pred-{i}",
            f"SHP-{i:06d}",
            0.5 + (i % 10) * 0.05,
            json.dumps({"corridor": 0.4, "vessel": 0.3, "manifest": 0.3}),
            json.dumps({"lower": 0.4, "upper": 0.7}),
            now - timedelta(hours=12 - (i % 12))
        ))

    # Shipments
    origins = ['CN', 'MX', 'IN', 'VN', 'HK']
    commodities = ['ELEC', 'TEXTL', 'MACH', 'CHEM', 'AUTOS']
    for i in range(100):
        cursor.execute("""
            INSERT INTO shipments VALUES
            (?, ?, ?, 'US', '1234567890', ?, ?, ?, ?, 'processing', ?, ?, ?, ?, ?)
        """, (
            f"SHP-{i:06d}",
            f"MAN-{i:05d}",
            origins[i % 5],
            10000 + (i * 500),
            5000 + (i * 100),
            f"Shipper {i}",
            f"Consignee {i}",
            0.5 + (i % 10) * 0.05,
            json.dumps({"corridor": 0.4, "vessel": 0.3, "manifest": 0.3}),
            json.dumps({"lower": 0.4, "upper": 0.7}),
            now - timedelta(hours=24 - (i % 24)),
            now - timedelta(hours=12 - (i % 12))
        ))

    conn.commit()
    conn.close()

    # Use SQLAlchemy for ORM session
    engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()

    try:
        yield session
    finally:
        session.close()
        # Cleanup
        if TEST_DB_PATH.exists():
            TEST_DB_PATH.unlink()


@pytest.fixture(scope="function")
def mock_db_session():
    """Mock database session for unit tests"""
    session = MagicMock(spec=Session)
    session.query = MagicMock()
    session.add = MagicMock()
    session.commit = MagicMock()
    session.rollback = MagicMock()
    session.close = MagicMock()
    return session


# ============================================================================
# DATA SERVICE FIXTURES
# ============================================================================

@pytest.fixture(scope="function")
async def data_service(db_session):
    """
    Initialize RiskModelDataService with test database.

    Returns:
        Service instance configured with test DB and mock risk engine.
    """
    from services.data.db import RiskModelDataService

    service = RiskModelDataService(
        db_session=db_session,
        risk_engine_url="http://localhost:8004",
        db_path=str(TEST_DB_PATH)
    )
    return service


# ============================================================================
# MOCK SERVICE FIXTURES
# ============================================================================

@pytest.fixture(scope="function")
def mock_risk_engine() -> Dict[str, Any]:
    """
    Mock precise-risk-engine service responses.

    Returns a mock object that simulates the risk engine API with:
    - Score predictions
    - SHAP explainability factors
    - Latency metrics
    """
    mock = MagicMock()

    async def mock_predict(shipment: Dict[str, Any], model_version: str = "v3.0"):
        """Mock prediction response"""
        return {
            'shipment_id': shipment.get('id', 'SHP-000000'),
            'model_version': model_version,
            'score': 0.76,
            'confidence': 0.91,
            'latency_ms': 85,
            'components': {
                'corridor_score': 0.65,
                'vessel_score': 0.72,
                'manifest_score': 0.81
            },
            'shap': {
                'base_score': 0.35,
                'positive': [
                    {'feature': 'documentation_risk', 'contribution': 0.16},
                    {'feature': 'routing_risk', 'contribution': 0.14},
                    {'feature': 'shipper_history', 'contribution': 0.11}
                ],
                'negative': [
                    {'feature': 'party_trust_score', 'contribution': -0.04},
                    {'feature': 'compliance_record', 'contribution': -0.02}
                ]
            }
        }

    async def mock_explain(shipment_id: str, model_version: str = "v3.0"):
        """Mock SHAP explanation response"""
        return {
            'shipment_id': shipment_id,
            'model_version': model_version,
            'explanation': {
                'base_value': 0.35,
                'features': {
                    'documentation_risk': {'value': 1.0, 'impact': 0.16},
                    'routing_risk': {'value': 0.8, 'impact': 0.14},
                    'shipper_age_months': {'value': 24, 'impact': 0.11},
                    'vessel_flag': {'value': 'PK', 'impact': 0.08}
                }
            }
        }

    mock.predict = mock_predict
    mock.explain = mock_explain
    return mock


@pytest.fixture(scope="function")
def mock_senzing() -> MagicMock:
    """Mock Senzing entity resolution service"""
    mock = MagicMock()

    async def mock_search_by_attributes(attributes: Dict[str, Any]):
        """Mock entity search response"""
        return {
            'resolved_entities': [
                {
                    'entity_id': '1001',
                    'match_score': 85,
                    'name': attributes.get('shipper_name', 'Unknown'),
                    'country': attributes.get('origin_country', 'US'),
                    'entity_type': 'SHIPPER'
                }
            ],
            'possible_matches': [
                {
                    'entity_id': '1002',
                    'match_score': 72,
                    'name': 'Similar Shipper',
                    'country': 'CN'
                }
            ]
        }

    mock.search_by_attributes = mock_search_by_attributes
    return mock


@pytest.fixture(scope="function")
def mock_vessel_api() -> MagicMock:
    """Mock VesselAPI service for ship tracking"""
    mock = MagicMock()

    async def mock_get_vessel_info(imo: str):
        """Mock vessel information response"""
        return {
            'imo': imo,
            'vessel_name': 'EVER GIVEN',
            'vessel_type': 'Container Ship',
            'flag': 'PK',
            'length': 400,
            'gross_tonnage': 220000,
            'year_built': 2018,
            'risk_score': 0.35
        }

    mock.get_vessel_info = mock_get_vessel_info
    return mock


# ============================================================================
# API CLIENT FIXTURES
# ============================================================================

@pytest.fixture(scope="function")
async def api_client(mock_db_session, mock_risk_engine):
    """
    FastAPI test client for integration testing.

    Yields:
        TestClient configured with mock dependencies and test configuration.
    """
    from api.main import app
    from api.core.config import Settings

    # Override settings for test
    test_settings = Settings(
        environment="test",
        debug=True,
        database_url=TEST_DB_URL,
        demo_mode=True,
        use_mock_senzing=True
    )

    # Override dependency injections
    def override_get_settings():
        return test_settings

    def override_get_db():
        return mock_db_session

    app.dependency_overrides[Settings] = override_get_settings
    # app.dependency_overrides[get_db] = override_get_db

    client = TestClient(app)
    yield client

    # Cleanup
    app.dependency_overrides.clear()


# ============================================================================
# TEST DATA FIXTURES
# ============================================================================

@pytest.fixture(scope="function")
async def sample_shipment() -> Dict[str, Any]:
    """
    Create a realistic sample shipment for testing.

    Returns:
        Dictionary with complete shipment data matching Shipment model.
    """
    return {
        'id': 'SHP-00142857',
        'manifest_id': 'MAN-01234',
        'shipper_name': 'Shanghai Electronics Co.',
        'consignee_name': 'Tech Import Inc.',
        'origin_country': 'CN',
        'destination_country': 'US',
        'hs_code': '8517.62.00',
        'declared_value_usd': 45200,
        'declared_weight_kg': 2000,
        'commodity_name': 'Electronic Components',
        'vessel_name': 'EVER GIVEN',
        'container_type': '40ft FCL',
        'status': 'processing'
    }


@pytest.fixture(scope="function")
async def sample_shipments() -> list:
    """Load sample shipments from fixture file"""
    fixture_path = FIXTURES_DIR / "shipments.json"
    if fixture_path.exists():
        with open(fixture_path, 'r') as f:
            return json.load(f)
    return []


@pytest.fixture(scope="function")
def sample_shap_responses() -> list:
    """Load sample SHAP responses from fixture file"""
    fixture_path = FIXTURES_DIR / "shap_responses.json"
    if fixture_path.exists():
        with open(fixture_path, 'r') as f:
            return json.load(f)
    return []


@pytest.fixture(scope="function")
def sample_risk_breakdown() -> Dict[str, Any]:
    """Sample risk score breakdown"""
    return {
        'corridor_score': 0.65,
        'corridor_components': {
            'route_frequency': 0.7,
            'trade_volume': 0.6,
            'previous_violations': 0.65
        },
        'vessel_score': 0.72,
        'vessel_components': {
            'flag_risk': 0.75,
            'ship_age': 0.7,
            'previous_seizures': 0.71
        },
        'manifest_score': 0.81,
        'manifest_components': {
            'documentation_completeness': 0.85,
            'commodity_match': 0.79,
            'value_consistency': 0.79
        }
    }


# ============================================================================
# PYTEST CONFIGURATION
# ============================================================================

def pytest_configure(config):
    """Configure pytest with custom markers and settings"""
    config.addinivalue_line("markers", "asyncio: mark test as async")
    config.addinivalue_line("markers", "unit: mark test as unit test")
    config.addinivalue_line("markers", "integration: mark test as integration test")
    config.addinivalue_line("markers", "smoke: mark test as smoke test")
    config.addinivalue_line("markers", "slow: mark test as slow (> 1 second)")


def pytest_collection_modifyitems(config, items):
    """Add asyncio marker to async tests automatically"""
    for item in items:
        if asyncio.iscoroutinefunction(item.function):
            item.add_marker(pytest.mark.asyncio)


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Set up test environment variables"""
    os.environ["ENVIRONMENT"] = "test"
    os.environ["DEBUG"] = "true"
    os.environ["DEMO_MODE"] = "true"
    os.environ["USE_MOCK_SENZING"] = "true"
    os.environ["CBP_API_URL"] = "http://localhost:8000"
    os.environ["RISK_ENGINE_URL"] = "http://localhost:8004"
    yield
    # Cleanup would go here
