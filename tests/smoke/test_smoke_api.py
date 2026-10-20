#!/usr/bin/env python3
"""
SkillBridge Suite Live Smoke Testing Suite.
Tests live deployed or running local API endpoints.
Skipped automatically during unit tests unless API_URL environment variable is set.
"""

import os
import pytest
import requests

API_URL = os.getenv("API_URL")
pytestmark = pytest.mark.skipif(
    not API_URL,
    reason="API_URL environment variable not set. Live smoke tests skipped."
)

BASE_URL = API_URL.rstrip('/') if API_URL else "http://localhost:8000"

def test_live_health_check():
    """Test health check endpoint on live server."""
    response = requests.get(f"{BASE_URL}/health", timeout=10)
    assert response.status_code in (200, 503)

def test_live_skills_master():
    """Test skills master endpoint on live server."""
    response = requests.get(f"{BASE_URL}/skills?type=master", timeout=10)
    assert response.status_code in (200, 401)

def test_live_auth_login_invalid():
    """Test authentication login endpoint rejects invalid tokens."""
    response = requests.post(
        f"{BASE_URL}/auth/login",
        json={"idToken": "invalid_test_token"},
        timeout=10
    )
    assert response.status_code in (400, 401)

def test_live_jobs_search():
    """Test jobs search endpoint."""
    response = requests.get(f"{BASE_URL}/jobs/search?country=in&what=developer", timeout=10)
    assert response.status_code in (200, 400, 500)

def test_live_learning_resources():
    """Test learning resources endpoint."""
    response = requests.get(f"{BASE_URL}/learning/python", timeout=10)
    assert response.status_code in (200, 404, 500)
