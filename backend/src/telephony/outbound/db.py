import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "farm_memory.db")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    cursor = conn.cursor()

    # Table for Farmer Profiles
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS farmers (
            user_id TEXT PRIMARY KEY,
            name TEXT,
            crops_grown TEXT,
            land_size TEXT,
            district TEXT,
            irrigation_type TEXT,
            language_preference TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Table for Escalations
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS escalations (
            ticket_id TEXT PRIMARY KEY,
            farmer_name TEXT,
            reason TEXT,
            summary TEXT,
            urgency TEXT,
            language TEXT,
            preferred_contact TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Table for Call Outcomes (Day 8 Analytics)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS call_logs (
            call_id TEXT PRIMARY KEY,
            user_id TEXT,
            channel TEXT,
            status TEXT,
            reason TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()


def save_farmer(
    user_id,
    name,
    crops_grown="",
    land_size="",
    district="",
    irrigation_type="",
    language_preference="EN",
):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO farmers (user_id, name, crops_grown, land_size, district, irrigation_type, language_preference, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(user_id) DO UPDATE SET
            name=excluded.name,
            crops_grown=excluded.crops_grown,
            land_size=excluded.land_size,
            district=excluded.district,
            irrigation_type=excluded.irrigation_type,
            language_preference=excluded.language_preference,
            updated_at=CURRENT_TIMESTAMP
    """,
        (
            user_id,
            name,
            crops_grown,
            land_size,
            district,
            irrigation_type,
            language_preference,
        ),
    )
    conn.commit()
    conn.close()


def get_farmer(user_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM farmers WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return dict(row)
    return None


def save_escalation(
    farmer_name,
    reason,
    summary,
    urgency,
    language,
    preferred_contact,
):
    conn = get_db()
    cursor = conn.cursor()
    ticket_id = f"ESC-{int(datetime.now().timestamp())}"
    cursor.execute(
        """
        INSERT INTO escalations (ticket_id, farmer_name, reason, summary, urgency, language, preferred_contact)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """,
        (
            ticket_id,
            farmer_name,
            reason,
            summary,
            urgency,
            language,
            preferred_contact,
        ),
    )
    conn.commit()
    conn.close()
    return ticket_id


# ============================================================
# DAY 8: CALL METRICS & LOGGING
# ============================================================

def log_call_outcome(call_id, user_id, channel, status, reason):
    """Saves a call log entry to the database."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT OR REPLACE INTO call_logs (call_id, user_id, channel, status, reason)
        VALUES (?, ?, ?, ?, ?)
    """,
        (call_id, user_id, channel, status, reason),
    )
    conn.commit()
    conn.close()


def get_dashboard_stats():
    """Fetches metrics for Streamlit Dashboard."""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM call_logs")
    total = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM call_logs WHERE status = 'SUCCESS'")
    successful = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM call_logs WHERE status = 'FAILED'")
    failed = cursor.fetchone()[0]

    cursor.execute(
        "SELECT call_id, channel, status, reason, created_at FROM call_logs ORDER BY created_at DESC LIMIT 10"
    )
    recent = cursor.fetchall()

    conn.close()

    return {
        "total": total,
        "successful": successful,
        "failed": failed,
        "recent": [dict(r) for r in recent],
    }