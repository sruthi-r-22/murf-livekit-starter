import sqlite3
import random
import string
from datetime import datetime

def init_escalation_db():
    conn = sqlite3.connect("farm_memory.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS escalations (
            ticket_id TEXT PRIMARY KEY,
            farmer_name TEXT,
            reason TEXT,
            summary TEXT,
            urgency TEXT,
            language TEXT,
            preferred_contact TEXT,
            status TEXT,
            created_at TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

def save_escalation(farmer_name: str, reason: str, summary: str, urgency: str, language: str, preferred_contact: str) -> str:
    ticket_id = f"ESC-{''.join(random.choices(string.digits, k=4))}"
    conn = sqlite3.connect("farm_memory.db")
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO escalations (ticket_id, farmer_name, reason, summary, urgency, language, preferred_contact, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, 'OPEN', ?)
    """, (ticket_id, farmer_name, reason, summary, urgency, language, preferred_contact, datetime.now().isoformat()))
    conn.commit()
    conn.close()
    return ticket_id