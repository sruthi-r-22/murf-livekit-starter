import sqlite3
import json
from datetime import datetime
from pathlib import Path


# ============================================================
# DATABASE LOCATION
# ============================================================

# Always store the database next to this db.py file.
# This prevents different LiveKit processes from accidentally
# opening different databases.

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "farm_memory.db"


# ============================================================
# DATABASE CONNECTION
# ============================================================

def get_connection():
    return sqlite3.connect(str(DB_PATH))


# ============================================================
# INITIALIZE DATABASE
# ============================================================

def init_db():
    conn = get_connection()

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS farmers (
            user_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            language_preference TEXT DEFAULT 'EN',
            crops_grown TEXT DEFAULT '',
            land_size TEXT DEFAULT '',
            district TEXT DEFAULT '',
            irrigation_type TEXT DEFAULT '',
            facts TEXT DEFAULT '{}',
            last_interaction TEXT
        )
        """
    )

    conn.commit()
    conn.close()

    print(f"Database initialized at: {DB_PATH}")


# ============================================================
# GET FARMER
# ============================================================

def get_farmer(user_id: str):
    conn = get_connection()

    cursor = conn.execute(
        """
        SELECT
            user_id,
            name,
            language_preference,
            crops_grown,
            land_size,
            district,
            irrigation_type,
            facts,
            last_interaction
        FROM farmers
        WHERE user_id = ?
        """,
        (user_id,)
    )

    row = cursor.fetchone()

    conn.close()

    if not row:
        return None

    return {
        "user_id": row[0],
        "name": row[1],
        "language_preference": row[2],
        "crops_grown": row[3],
        "land_size": row[4],
        "district": row[5],
        "irrigation_type": row[6],
        "facts": json.loads(row[7] or "{}"),
        "last_interaction": row[8],
    }


# ============================================================
# SAVE FARMER
# ============================================================

def save_farmer(
    user_id: str,
    name: str,
    crops_grown: str = "",
    land_size: str = "",
    district: str = "",
    irrigation_type: str = "",
    language_preference: str = "EN",
    facts: dict | None = None,
):
    if facts is None:
        facts = {}

    now = datetime.now().isoformat()

    conn = get_connection()

    conn.execute(
        """
        INSERT INTO farmers (
            user_id,
            name,
            language_preference,
            crops_grown,
            land_size,
            district,
            irrigation_type,
            facts,
            last_interaction
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)

        ON CONFLICT(user_id)
        DO UPDATE SET
            name = excluded.name,
            language_preference = excluded.language_preference,
            crops_grown = excluded.crops_grown,
            land_size = excluded.land_size,
            district = excluded.district,
            irrigation_type = excluded.irrigation_type,
            facts = excluded.facts,
            last_interaction = excluded.last_interaction
        """,
        (
            user_id,
            name,
            language_preference,
            crops_grown,
            land_size,
            district,
            irrigation_type,
            json.dumps(facts),
            now,
        )
    )

    conn.commit()
    conn.close()

    return f"Successfully saved memory for {name}."


# ============================================================
# DELETE FARMER
# ============================================================

def delete_farmer(user_id: str):
    conn = get_connection()

    conn.execute(
        "DELETE FROM farmers WHERE user_id = ?",
        (user_id,)
    )

    conn.commit()
    conn.close()

    return True


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":
    init_db()

    print("Database path:")
    print(DB_PATH)

    print("\nCurrent default farmer:")
    print(get_farmer("default_farmer"))