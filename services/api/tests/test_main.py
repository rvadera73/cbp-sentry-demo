"""Test main application"""
import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_health_check():
    """Test health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "environment" in data
    assert "debug" in data


def test_not_found():
    """Test 404 handling"""
    response = client.get("/nonexistent")
    assert response.status_code == 404
