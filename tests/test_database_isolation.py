import os
import sqlite3
import pytest
from fastapi.testclient import TestClient

from backend.app.core.database import engine, get_database_url
from backend.app.models.case import Case

def test_database_url_is_isolated_in_tests():
    """Verify that tests run against an in-memory or isolated database, never counterpulse.db."""
    url = get_database_url()
    assert ":memory:" in url or "test" in url
    assert "counterpulse.db" not in url

def test_testclient_does_not_pollute_production_database(client: TestClient):
    """Verify that case creation during test execution does NOT write to counterpulse.db."""
    dev_db_path = "counterpulse.db"
    initial_count = 0
    if os.path.exists(dev_db_path):
        conn = sqlite3.connect(dev_db_path)
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM cases")
        initial_count = cur.fetchone()[0]
        conn.close()

    # Create a test case via client
    res = client.post(
        "/api/v1/cases",
        json={
            "title": "Isolation Regression Verification Case",
            "description": "Ensures no leak into runtime database",
        },
    )
    assert res.status_code == 201

    if os.path.exists(dev_db_path):
        conn = sqlite3.connect(dev_db_path)
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM cases")
        final_count = cur.fetchone()[0]
        conn.close()
        assert final_count == initial_count, "Test case leaked into development database!"
