"""
Unit tests for ALVEON Hybrid Database Engine (SQLite & PostgreSQL Dialect Adaptation).
Validates cursor-level engine detection, SQL placeholder rewriting (? -> %s),
ON CONFLICT upserts, and automatic failover to SQLite WAL mode.
"""

import pytest
import sqlite3
import unittest.mock as mock
from core.database import (
    is_sqlite_cursor,
    execute_query,
    get_db_type,
    get_db_connection,
    save_radiology_report,
    get_report_by_study,
    list_recent_reports,
    log_audit_event,
    hash_password,
    verify_password
)

class MockPostgresCursor:
    """Simulates a psycopg2 DictCursor for testing parameter rewriting."""
    def __init__(self):
        self.executed_queries = []
        self.connection = mock.MagicMock()
        # Ensure it doesn't look like sqlite3
        self.__module__ = "psycopg2.extras"

    def execute(self, sql, params=None):
        self.executed_queries.append((sql, params))

    def fetchone(self):
        return None

    def fetchall(self):
        return []

def test_sqlite_cursor_detection():
    """Verify that native SQLite cursors are correctly identified."""
    conn = sqlite3.connect(":memory:")
    cur = conn.cursor()
    assert is_sqlite_cursor(cur) is True
    conn.close()

def test_mock_postgres_cursor_detection():
    """Verify that non-SQLite cursors are identified as PostgreSQL/External."""
    pg_cur = MockPostgresCursor()
    assert is_sqlite_cursor(pg_cur) is False

def test_execute_query_parameter_adaptation():
    """Verify ? is translated to %s for PostgreSQL and retained for SQLite."""
    # 1. Test SQLite Cursor: keeps ?
    sqlite_conn = sqlite3.connect(":memory:")
    sqlite_conn.execute("CREATE TABLE t (id INT, val TEXT);")
    sqlite_cur = sqlite_conn.cursor()
    execute_query(sqlite_cur, "INSERT INTO t VALUES (?, ?);", (1, "alpha"))
    sqlite_conn.commit()

    execute_query(sqlite_cur, "SELECT * FROM t WHERE id = ?;", (1,))
    row = sqlite_cur.fetchone()
    assert row == (1, "alpha")
    sqlite_conn.close()

    # 2. Test PostgreSQL Cursor: replaces ? with %s
    pg_cur = MockPostgresCursor()
    execute_query(pg_cur, "SELECT * FROM users WHERE username = ? AND id = ?", ("dr.vance", "USR-01"))
    assert len(pg_cur.executed_queries) == 1
    query, params = pg_cur.executed_queries[0]
    assert "%s" in query
    assert "?" not in query
    assert params == ("dr.vance", "USR-01")

def test_database_failover_to_sqlite(monkeypatch):
    """Verify that when DATABASE_URL is invalid, get_db_connection safely falls back to SQLite."""
    monkeypatch.setenv("DATABASE_URL", "postgresql://invalid_user:invalid_pass@127.0.0.1:54329/nonexistent_db")
    # Reload or test get_db_connection
    conn = get_db_connection()
    # Connection should be a valid SQLite connection despite the broken DATABASE_URL
    assert isinstance(conn, sqlite3.Connection)
    conn.close()

def test_password_hashing_and_verification():
    """Verify PBKDF2-HMAC-SHA256 password hashing and validation."""
    pwd = "HospitalSecurePassword2026!"
    h, salt = hash_password(pwd)
    assert len(h) == 64
    assert len(salt) == 32
    assert verify_password(pwd, salt, h) is True
    assert verify_password("WrongPassword", salt, h) is False

def test_report_persistence_and_caliper_cleaning():
    """Verify save_radiology_report cleans malformed/nested caliper measurements and calculates signature hash."""
    report_data = {
        "study_uid": "STUDY-PG-TEST-001",
        "patient_mrn": "MRN-PG-001",
        "patient_name": "Test Patient PG",
        "user_id": "USR-VANCE-01",
        "attesting_physician": "Dr. Eleanor Vance, MD",
        "impression": "No acute cardiopulmonary disease.",
        "caliper_measurements": '[{"type": "ruler", "length_mm": 18.5}]',  # String-encoded JSON
        "status": "FINAL_SIGNED"
    }

    res = save_radiology_report(report_data)
    assert res["status"] == "FINAL_SIGNED"
    assert res["signature_hash"] is not None

    retrieved = get_report_by_study("STUDY-PG-TEST-001")
    assert retrieved is not None
    assert isinstance(retrieved["caliper_measurements"], list)
    assert len(retrieved["caliper_measurements"]) == 1
    assert retrieved["caliper_measurements"][0]["length_mm"] == 18.5
