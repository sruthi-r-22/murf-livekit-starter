import sqlite3
import random
import datetime
import httpx

DB_FILE = "farm_memory.db"

# Replace with your real Webhook URL (e.g. Webhook.site URL or Discord Webhook)
WEBHOOK_URL = "https://webhook.site/YOUR-UNIQUE-WEBHOOK-ID"

def init_db():
    conn = sqlite3.connect(DB_FILE)
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
            created_at TEXT
        )
    """)
    conn.commit()
    conn.close()

def save_farmer(user_id, name, crops_grown="", land_size="", district="", irrigation_type="", language_preference="EN"):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO farmers (user_id, name, crops_grown, land_size, district, irrigation_type, language_preference)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            name=excluded.name,
            crops_grown=excluded.crops_grown,
            land_size=excluded.land_size,
            district=excluded.district,
            irrigation_type=excluded.irrigation_type,
            language_preference=excluded.language_preference
    """, (user_id, name, crops_grown, land_size, district, irrigation_type, language_preference))
    conn.commit()
    conn.close()

def get_farmer(user_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT name, crops_grown, land_size, district, irrigation_type, language_preference FROM farmers WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return {
            "name": row[0],
            "crops_grown": row[1],
            "land_size": row[2],
            "district": row[3],
            "irrigation_type": row[4],
            "language_preference": row[5]
        }
    return None

def dispatch_webhook_notification(ticket_id, farmer_name, reason, summary, urgency, preferred_contact):
    """Sends escalation details out to a real endpoint (Webhook.site / Discord)."""
    if "YOUR-UNIQUE-WEBHOOK-ID" in WEBHOOK_URL:
        print("[Webhook] URL not configured. Request saved locally to SQLite.")
        return

    payload = {
        "event": "human_escalation_requested",
        "ticket_id": ticket_id,
        "farmer_name": farmer_name,
        "urgency": urgency,
        "reason": reason,
        "summary": summary,
        "preferred_contact": preferred_contact,
        "timestamp": datetime.datetime.now().isoformat()
    }

    try:
        response = httpx.post(WEBHOOK_URL, json=payload, timeout=5.0)
        print(f"[Webhook Success] Status Code: {response.status_code}")
    except Exception as e:
        print(f"[Webhook Error] {e}")

def save_escalation(farmer_name, reason, summary, urgency="MEDIUM", language="English", preferred_contact="Phone Call"):
    ticket_id = f"FM-A{random.randint(10, 99)}F{random.randint(10, 99)}"
    created_at = datetime.datetime.now().isoformat()

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO escalations (ticket_id, farmer_name, reason, summary, urgency, language, preferred_contact, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (ticket_id, farmer_name, reason, summary, urgency, language, preferred_contact, created_at))
    conn.commit()
    conn.close()

    dispatch_webhook_notification(ticket_id, farmer_name, reason, summary, urgency, preferred_contact)

    return ticket_id