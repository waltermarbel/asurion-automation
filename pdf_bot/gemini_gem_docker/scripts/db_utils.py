import os
import psycopg2
import json

# Database config – read from environment with sensible defaults
DB_HOST = os.getenv("DB_HOST", "db")
DB_NAME = os.getenv("DB_NAME", "gemini_gem")
DB_USER = os.getenv("DB_USER", "gem_admin")
DB_PASS = os.getenv("DB_PASS", "secure_password_123")

def get_connection():
    """Establish connection to the PostgreSQL service."""
    try:
        return psycopg2.connect(
            host=DB_HOST,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASS
        )
    except Exception as e:
        print(f"[DB Error] Connection failed: {e}")
        return None

def log_system_event(actor, action, details):
    """Write to system_log for forensic traceability."""
    conn = get_connection()
    if not conn:
        return
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO system_log (actor, action, details) VALUES (%s, %s, %s)",
                (actor, action, json.dumps(details))
            )
        conn.commit()
    except Exception as e:
        print(f"[Log Error] {e}")
    finally:
        conn.close()
