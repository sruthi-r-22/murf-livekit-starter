import logging
import os
import sqlite3
import pandas as pd

logger = logging.getLogger("db")

# ============================================================
# DATABASE PATH
# ============================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_NAME = os.path.join(BASE_DIR, "farm_memory.db")


def get_connection():
    return sqlite3.connect(DB_NAME, timeout=10.0)


# ============================================================
# DATABASE INITIALIZATION
# ============================================================

def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS farmers (
            user_id TEXT PRIMARY KEY,
            name TEXT,
            crops_grown TEXT,
            land_size TEXT,
            district TEXT,
            irrigation_type TEXT,
            language_preference TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS escalations (
            ticket_id TEXT PRIMARY KEY,
            farmer_name TEXT,
            reason TEXT,
            summary TEXT,
            urgency TEXT,
            language TEXT,
            preferred_contact TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS call_outcomes (
            call_id TEXT PRIMARY KEY,
            user_id TEXT,
            channel TEXT,
            status TEXT,
            reason TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()

    logger.info("Database initialized successfully at: %s", DB_NAME)


# ============================================================
# FARMER PROFILE
# ============================================================

def get_farmer(user_id: str):
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM farmers WHERE user_id = ?",
        (user_id,)
    )

    row = cursor.fetchone()
    conn.close()

    return dict(row) if row else None


def save_farmer(
    user_id: str,
    name: str,
    crops_grown: str = "",
    land_size: str = "",
    district: str = "",
    irrigation_type: str = "",
    language_preference: str = "EN",
):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO farmers (
            user_id,
            name,
            crops_grown,
            land_size,
            district,
            irrigation_type,
            language_preference
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)

        ON CONFLICT(user_id) DO UPDATE SET
            name = excluded.name,
            crops_grown = excluded.crops_grown,
            land_size = excluded.land_size,
            district = excluded.district,
            irrigation_type = excluded.irrigation_type,
            language_preference = excluded.language_preference
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


# ============================================================
# ESCALATION TICKETS
# ============================================================

def save_escalation(
    farmer_name: str,
    reason: str,
    summary: str,
    urgency: str,
    language: str,
    preferred_contact: str,
) -> str:

    import uuid

    ticket_id = f"TICK-{uuid.uuid4().hex[:6].upper()}"

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO escalations (
            ticket_id,
            farmer_name,
            reason,
            summary,
            urgency,
            language,
            preferred_contact
        )
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
# CALL OUTCOME
# ============================================================

def log_call_outcome(
    call_id: str,
    user_id: str,
    channel: str,
    status: str,
    reason: str,
):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO call_outcomes (
            call_id,
            user_id,
            channel,
            status,
            reason
        )
        VALUES (?, ?, ?, ?, ?)

        ON CONFLICT(call_id) DO UPDATE SET
            user_id = excluded.user_id,
            channel = excluded.channel,
            status = excluded.status,
            reason = excluded.reason
        """,
        (
            call_id,
            user_id,
            channel,
            status,
            reason,
        ),
    )

    conn.commit()
    conn.close()

    logger.info(
        "Logged Call Outcome: %s -> %s (%s)",
        call_id,
        status,
        reason,
    )


# ============================================================
# DASHBOARD STATISTICS
# ============================================================

def get_dashboard_stats():

    conn = get_connection()
    cursor = conn.cursor()

    # Total calls
    cursor.execute("""
        SELECT COUNT(*)
        FROM call_outcomes
    """)
    total_calls = cursor.fetchone()[0] or 0

    # Successful calls
    cursor.execute("""
        SELECT COUNT(*)
        FROM call_outcomes
        WHERE UPPER(status) = 'SUCCESS'
    """)
    successful_calls = cursor.fetchone()[0] or 0

    # Failed calls
    cursor.execute("""
        SELECT COUNT(*)
        FROM call_outcomes
        WHERE UPPER(status) = 'FAILED'
    """)
    failed_calls = cursor.fetchone()[0] or 0

    # Recent calls
    df_calls = pd.read_sql_query(
        """
        SELECT
            call_id AS "Call ID",
            channel AS "Channel",
            status AS "Status",
            reason AS "Reason",
            timestamp AS "Timestamp"
        FROM call_outcomes
        ORDER BY timestamp DESC
        LIMIT 20
        """,
        conn,
    )

    conn.close()

    # Convert dataframe into records for dashboard.py
    recent_calls = df_calls.values.tolist()

    return {
        # Main metrics
        "total": total_calls,
        "successful": successful_calls,
        "failed": failed_calls,

        # Alternative names
        "total_calls": total_calls,
        "successful_calls": successful_calls,
        "failed_calls": failed_calls,

        # Dashboard recent calls
        "recent": recent_calls,

        # Also keep dataframe available
        "calls_df": df_calls,
    }


# ============================================================
# INITIALIZE DATABASE
# ============================================================

init_db()