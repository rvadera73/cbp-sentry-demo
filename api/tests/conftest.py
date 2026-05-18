"""Test fixtures"""
import pytest
from fastapi.testclient import TestClient
from main import app


@pytest.fixture
def client():
    """FastAPI test client"""
    return TestClient(app)


@pytest.fixture
async def db():
    """Database fixture"""
    # TODO: Initialize test database
    yield
    # TODO: Cleanup
