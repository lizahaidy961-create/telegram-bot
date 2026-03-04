import os
import psycopg2
from psycopg2.extras import RealDictCursor

DATABASE_URL = os.environ.get("DATABASE_URL")

def get_connection():
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)

def create_table():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS subscribers (
            id SERIAL PRIMARY KEY,
            telegram_id BIGINT UNIQUE,
            stripe_customer_id TEXT,
            stripe_subscription_id TEXT UNIQUE,
            status TEXT
        );
    """)
    conn.commit()
    cur.close()
    conn.close()