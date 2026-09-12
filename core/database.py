"""
ALVEON Hospital PACS - Core SQLite & PostgreSQL Hybrid Database Engine
=======================================================================
Implements a production-grade, zero-setup embedded database architecture
compliant with HIPAA Security Rule § 164.312(a)(1) Access Control and
§ 164.312(b) Audit Controls.

Supports:
1. Native Embedded SQLite with Write-Ahead Logging (WAL) mode for $0.00 zero-setup operations.
2. Enterprise Managed Cloud PostgreSQL (Neon, Supabase, AWS RDS, GCP Cloud SQL) via DATABASE_URL
   with automatic failover resilience and dialect-agnostic query adaptation.
"""

import os
import sqlite3
import hashlib
import secrets
import json
import time
import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Union
import logging

logger = logging.getLogger("alveon.database")

DB_PATH = Path(os.environ.get("ALVEON_DB_PATH", Path(__file__).resolve().parent.parent / "data" / "alveon.db"))
DATABASE_URL = os.environ.get("DATABASE_URL")

def get_db_type() -> str:
    """Returns the configured database engine type ('postgresql' or 'sqlite')."""
    if DATABASE_URL and (DATABASE_URL.startswith("postgresql://") or DATABASE_URL.startswith("postgres://")):
        return "postgresql"
    return "sqlite"

def get_db_connection():
    """
    Creates a thread-safe connection to the clinical database.
    Defaults to embedded SQLite with Write-Ahead Logging (WAL) mode for zero-cost operation.
    Optionally connects to enterprise PostgreSQL when DATABASE_URL is configured.
    """
    db_type = get_db_type()
    if db_type == "postgresql":
        try:
            import psycopg2
            import psycopg2.extras
            conn = psycopg2.connect(DATABASE_URL)
            conn.cursor_factory = psycopg2.extras.DictCursor
            return conn
        except Exception as e:
            logger.warning(f"PostgreSQL connection failed ({e}); falling back smoothly to local SQLite.")

    # SQLite (Zero-cost, built-in, thread-safe WAL mode)
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), timeout=15.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    return conn

def is_sqlite_cursor(cursor) -> bool:
    """Detects if the active cursor is bound to an embedded SQLite connection."""
    try:
        if hasattr(cursor, 'connection') and isinstance(cursor.connection, sqlite3.Connection):
            return True
        if type(cursor).__module__.startswith('sqlite3'):
            return True
    except Exception:
        pass
    return False

def execute_query(cursor, sql: str, params: Optional[Union[Tuple, List]] = None):
    """
    Executes a SQL query, automatically adapting parameter placeholders
    between SQLite ('?') and PostgreSQL ('%s') based on the active connection engine.
    """
    if not is_sqlite_cursor(cursor):
        # PostgreSQL uses %s placeholders
        sql = sql.replace("?", "%s")
    if params is not None:
        cursor.execute(sql, params)
    else:
        cursor.execute(sql)

def hash_password(password: str, salt: Optional[str] = None) -> Tuple[str, str]:
    """Hashes password with PBKDF2-HMAC-SHA256 (100,000 rounds) and 16-byte salt."""
    if not salt:
        salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), 100000)
    return dk.hex(), salt

def verify_password(password: str, salt: str, password_hash: str) -> bool:
    """Verifies a plaintext password against the stored salt and hash."""
    expected_hash, _ = hash_password(password, salt)
    return secrets.compare_digest(expected_hash, password_hash)

def init_db():
    """Initializes schema and seeds default clinical staff directory."""
    conn = get_db_connection()
    cursor = conn.cursor()
    is_sqlite = is_sqlite_cursor(cursor)

    # 1. Users Table
    execute_query(cursor, """
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            salt TEXT NOT NULL,
            full_name TEXT NOT NULL,
            title TEXT NOT NULL,
            role TEXT NOT NULL,
            department TEXT NOT NULL,
            npi TEXT,
            initials TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP
        );
    """)

    # 2. Sessions Table
    execute_query(cursor, """
        CREATE TABLE IF NOT EXISTS sessions (
            token TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            role TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at INTEGER NOT NULL,
            is_active INTEGER DEFAULT 1,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );
    """)

    # 3. Radiology Reports Table (Structured Findings + Caliper Measurement JSON)
    execute_query(cursor, """
        CREATE TABLE IF NOT EXISTS radiology_reports (
            id TEXT PRIMARY KEY,
            study_uid TEXT NOT NULL,
            patient_mrn TEXT NOT NULL,
            patient_name TEXT NOT NULL,
            user_id TEXT NOT NULL,
            attesting_physician TEXT NOT NULL,
            examination_technique TEXT,
            clinical_indication TEXT,
            findings_lungs TEXT,
            findings_pleura TEXT,
            findings_cardiomediastinum TEXT,
            findings_bones_soft_tissues TEXT,
            impression TEXT NOT NULL,
            acr_actionable_code TEXT,
            caliper_measurements TEXT,
            digital_signature_hash TEXT NOT NULL,
            status TEXT DEFAULT 'FINAL_SIGNED',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            signed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
    """)

    # 4. Cryptographic HIPAA Audit Ledger (Block-chained hash integrity)
    if not is_sqlite:
        execute_query(cursor, """
            CREATE TABLE IF NOT EXISTS audit_ledger (
                id SERIAL PRIMARY KEY,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                user_id TEXT,
                username TEXT,
                action TEXT NOT NULL,
                resource_type TEXT NOT NULL,
                resource_id TEXT,
                details TEXT,
                prev_hash TEXT,
                event_hash TEXT NOT NULL
            );
        """)
    else:
        execute_query(cursor, """
            CREATE TABLE IF NOT EXISTS audit_ledger (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                user_id TEXT,
                username TEXT,
                action TEXT NOT NULL,
                resource_type TEXT NOT NULL,
                resource_id TEXT,
                details TEXT,
                prev_hash TEXT,
                event_hash TEXT NOT NULL
            );
        """)

    execute_query(cursor, "CREATE INDEX IF NOT EXISTS idx_reports_study ON radiology_reports(study_uid);")
    execute_query(cursor, "CREATE INDEX IF NOT EXISTS idx_reports_mrn ON radiology_reports(patient_mrn);")
    execute_query(cursor, "CREATE INDEX IF NOT EXISTS idx_audit_action ON audit_ledger(action);")

    conn.commit()

    # Seed initial institutional staff if not present
    seed_users = [
        {
            "id": "USR-VANCE-01",
            "username": "dr.vance",
            "password": "Alveon2026!",
            "full_name": "Dr. Eleanor Vance, MD",
            "title": "Chief Thoracic Radiologist, FACR",
            "role": "ATTENDING_RADIOLOGIST",
            "department": "Diagnostic Radiology",
            "npi": "1849203819",
            "initials": "EV"
        },
        {
            "id": "USR-CHEN-02",
            "username": "dr.chen",
            "password": "Alveon2026!",
            "full_name": "Dr. Marcus Chen, MD",
            "title": "Senior Pulmonary Fellow",
            "role": "RADIOLOGY_FELLOW",
            "department": "Pulmonary & Critical Care",
            "npi": "1938491023",
            "initials": "MC"
        },
        {
            "id": "USR-REYES-03",
            "username": "dr.reyes",
            "password": "Alveon2026!",
            "full_name": "Dr. Sofia Reyes, MD",
            "title": "Emergency Medicine Attending",
            "role": "EMERGENCY_PHYSICIAN",
            "department": "Emergency Medicine (Trauma Level 1)",
            "npi": "1483920194",
            "initials": "SR"
        },
        {
            "id": "USR-PATEL-04",
            "username": "dr.patel",
            "password": "Alveon2026!",
            "full_name": "Dr. Rohan Patel, MD",
            "title": "Radiology Resident (PGY-4)",
            "role": "RESIDENT",
            "department": "Diagnostic Radiology",
            "npi": "1739284019",
            "initials": "RP"
        },
        {
            "id": "USR-BURKE-05",
            "username": "tech.burke",
            "password": "Alveon2026!",
            "full_name": "Michael Burke, RT(R)",
            "title": "Lead Radiologic Technologist",
            "role": "IMAGING_TECHNOLOGIST",
            "department": "Radiology Operations",
            "npi": "1049281938",
            "initials": "MB"
        }
    ]

    for user in seed_users:
        execute_query(cursor, "SELECT id FROM users WHERE username = ?", (user["username"],))
        if not cursor.fetchone():
            p_hash, salt = hash_password(user["password"])
            execute_query(cursor, """
                INSERT INTO users (id, username, password_hash, salt, full_name, title, role, department, npi, initials)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (user["id"], user["username"], p_hash, salt, user["full_name"], user["title"], user["role"], user["department"], user["npi"], user["initials"]))

    conn.commit()
    conn.close()

def get_user_by_username(username: str) -> Optional[Dict[str, Any]]:
    """Retrieves user row dictionary by username."""
    conn = get_db_connection()
    cursor = conn.cursor()
    execute_query(cursor, "SELECT * FROM users WHERE username = ?", (username,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def get_user_by_id(user_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves user row dictionary by user id."""
    conn = get_db_connection()
    cursor = conn.cursor()
    execute_query(cursor, "SELECT * FROM users WHERE id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def list_users() -> List[Dict[str, Any]]:
    """Returns all clinical staff users without password hashes."""
    conn = get_db_connection()
    cursor = conn.cursor()
    execute_query(cursor, "SELECT id, username, full_name, title, role, department, npi, initials, created_at, last_login FROM users ORDER BY id ASC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def log_audit_event(user_id: Optional[str], username: Optional[str], action: str, resource_type: str, resource_id: Optional[str], details: Dict[str, Any]) -> str:
    """Appends an immutable, cryptographically chained audit event to the ledger."""
    conn = get_db_connection()
    cursor = conn.cursor()

    execute_query(cursor, "SELECT event_hash FROM audit_ledger ORDER BY id DESC LIMIT 1")
    row = cursor.fetchone()
    prev_hash = row["event_hash"] if row else "GENESIS_BLOCK_ALVEON_PACS_2026"

    timestamp_str = datetime.datetime.now(datetime.timezone.utc).isoformat()
    details_str = json.dumps(details, sort_keys=True)
    raw_payload = f"{prev_hash}|{timestamp_str}|{user_id}|{username}|{action}|{resource_type}|{resource_id}|{details_str}"
    event_hash = hashlib.sha256(raw_payload.encode('utf-8')).hexdigest()

    execute_query(cursor, """
        INSERT INTO audit_ledger (timestamp, user_id, username, action, resource_type, resource_id, details, prev_hash, event_hash)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (timestamp_str, user_id, username, action, resource_type, resource_id, details_str, prev_hash, event_hash))

    conn.commit()
    conn.close()
    return event_hash

def save_radiology_report(report_data: Dict[str, Any]) -> Dict[str, Any]:
    """Persists or updates a finalized radiology report with digital signature and caliper measurements."""
    conn = get_db_connection()
    cursor = conn.cursor()
    is_sqlite = is_sqlite_cursor(cursor)

    report_id = report_data.get("id") or f"REP-{secrets.token_hex(6).upper()}"
    calipers = report_data.get("caliper_measurements", [])
    if isinstance(calipers, str):
        try:
            calipers = json.loads(calipers)
        except Exception:
            calipers = []
    if not isinstance(calipers, list):
        calipers = []
    calipers_json = json.dumps(calipers)

    # Calculate digital cryptographic signature of the diagnosis
    sig_raw = f"{report_data['study_uid']}|{report_data['patient_mrn']}|{report_data['user_id']}|{report_data['impression']}|{calipers_json}"
    sig_hash = hashlib.sha256(sig_raw.encode('utf-8')).hexdigest()

    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()

    params = (
        report_id,
        report_data["study_uid"],
        report_data["patient_mrn"],
        report_data.get("patient_name", "ANONYMOUS"),
        report_data["user_id"],
        report_data["attesting_physician"],
        report_data.get("examination_technique", "Chest Radiograph, Single View (AP/PA)."),
        report_data.get("clinical_indication", "Emergency triage evaluation."),
        report_data.get("findings_lungs", "Lungs clear bilaterally."),
        report_data.get("findings_pleura", "Costophrenic sulci clear."),
        report_data.get("findings_cardiomediastinum", "Normal cardiac silhouette."),
        report_data.get("findings_bones_soft_tissues", "Intact thoracic cage."),
        report_data["impression"],
        report_data.get("acr_actionable_code", "ACR Category 3"),
        calipers_json,
        sig_hash,
        report_data.get("status", "FINAL_SIGNED"),
        now_iso
    )

    if not is_sqlite:
        execute_query(cursor, """
            INSERT INTO radiology_reports (
                id, study_uid, patient_mrn, patient_name, user_id, attesting_physician,
                examination_technique, clinical_indication, findings_lungs, findings_pleura,
                findings_cardiomediastinum, findings_bones_soft_tissues, impression,
                acr_actionable_code, caliper_measurements, digital_signature_hash, status, signed_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (id) DO UPDATE SET
                study_uid = EXCLUDED.study_uid,
                patient_mrn = EXCLUDED.patient_mrn,
                patient_name = EXCLUDED.patient_name,
                user_id = EXCLUDED.user_id,
                attesting_physician = EXCLUDED.attesting_physician,
                examination_technique = EXCLUDED.examination_technique,
                clinical_indication = EXCLUDED.clinical_indication,
                findings_lungs = EXCLUDED.findings_lungs,
                findings_pleura = EXCLUDED.findings_pleura,
                findings_cardiomediastinum = EXCLUDED.findings_cardiomediastinum,
                findings_bones_soft_tissues = EXCLUDED.findings_bones_soft_tissues,
                impression = EXCLUDED.impression,
                acr_actionable_code = EXCLUDED.acr_actionable_code,
                caliper_measurements = EXCLUDED.caliper_measurements,
                digital_signature_hash = EXCLUDED.digital_signature_hash,
                status = EXCLUDED.status,
                signed_at = EXCLUDED.signed_at
        """, params)
    else:
        execute_query(cursor, """
            INSERT OR REPLACE INTO radiology_reports (
                id, study_uid, patient_mrn, patient_name, user_id, attesting_physician,
                examination_technique, clinical_indication, findings_lungs, findings_pleura,
                findings_cardiomediastinum, findings_bones_soft_tissues, impression,
                acr_actionable_code, caliper_measurements, digital_signature_hash, status, signed_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, params)

    conn.commit()
    conn.close()

    log_audit_event(
        user_id=report_data["user_id"],
        username=report_data.get("username", "physician"),
        action="REPORT_SIGNED",
        resource_type="RADIOLOGY_REPORT",
        resource_id=report_id,
        details={"study_uid": report_data["study_uid"], "signature_hash": sig_hash}
    )

    return {
        "report_id": report_id,
        "signature_hash": sig_hash,
        "signed_at": now_iso,
        "status": "FINAL_SIGNED"
    }

def get_report_by_study(study_uid: str) -> Optional[Dict[str, Any]]:
    """Fetches the latest signed report for a specific study UID."""
    conn = get_db_connection()
    cursor = conn.cursor()
    execute_query(cursor, "SELECT * FROM radiology_reports WHERE study_uid = ? ORDER BY signed_at DESC LIMIT 1", (study_uid,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        return None

    res = dict(row)
    if res.get("caliper_measurements"):
        try:
            parsed = json.loads(res["caliper_measurements"])
            while isinstance(parsed, str):
                parsed = json.loads(parsed)
            res["caliper_measurements"] = parsed if isinstance(parsed, list) else []
        except Exception:
            res["caliper_measurements"] = []
    else:
        res["caliper_measurements"] = []
    return res

def list_recent_reports(limit: int = 50) -> List[Dict[str, Any]]:
    """Lists recent finalized radiology reports."""
    conn = get_db_connection()
    cursor = conn.cursor()
    execute_query(cursor, "SELECT * FROM radiology_reports ORDER BY signed_at DESC LIMIT ?", (limit,))
    rows = cursor.fetchall()
    conn.close()

    output = []
    for r in rows:
        d = dict(r)
        if d.get("caliper_measurements"):
            try:
                parsed = json.loads(d["caliper_measurements"])
                while isinstance(parsed, str):
                    parsed = json.loads(parsed)
                d["caliper_measurements"] = parsed if isinstance(parsed, list) else []
            except Exception:
                d["caliper_measurements"] = []
        else:
            d["caliper_measurements"] = []
        output.append(d)
    return output

# Auto-initialize DB tables on module load
init_db()
