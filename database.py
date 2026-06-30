import os
import sqlite3
import psycopg2

DATABASE_URL = os.environ.get("DATABASE_URL")
DB_NAME = "customers.db"


class CursorWrapper:
    def __init__(self, cursor):
        self.cursor = cursor

    def execute(self, query, params=None):
        if DATABASE_URL:
            query = query.replace("?", "%s")
        if params is None:
            return self.cursor.execute(query)
        return self.cursor.execute(query, params)

    def fetchone(self):
        return self.cursor.fetchone()

    def fetchall(self):
        return self.cursor.fetchall()

    @property
    def lastrowid(self):
        return getattr(self.cursor, "lastrowid", None)


class ConnectionWrapper:
    def __init__(self, conn):
        self.conn = conn

    def cursor(self):
        return CursorWrapper(self.conn.cursor())

    def commit(self):
        self.conn.commit()

    def close(self):
        self.conn.close()


def get_db():
    if DATABASE_URL:
        return ConnectionWrapper(psycopg2.connect(DATABASE_URL))
    return ConnectionWrapper(sqlite3.connect(DB_NAME))


def is_postgres():
    return DATABASE_URL is not None


def init_db():
    conn = get_db()
    cur = conn.cursor()

    id_type = "SERIAL PRIMARY KEY" if DATABASE_URL else "INTEGER PRIMARY KEY AUTOINCREMENT"

    cur.execute(f"""
    CREATE TABLE IF NOT EXISTS customers (
        id {id_type},
        name TEXT NOT NULL,
        phone TEXT,
        address TEXT,
        created_at TEXT
    )
    """)

    cur.execute(f"""
    CREATE TABLE IF NOT EXISTS subscriptions (
        id {id_type},
        customer_id INTEGER,
        plan TEXT,
        start_date TEXT,
        memo TEXT,
        status TEXT,
        remaining_count INTEGER DEFAULT 12,
        next_shipping_date TEXT,
        created_at TEXT
    )
    """)

    cur.execute(f"""
    CREATE TABLE IF NOT EXISTS shipments (
        id {id_type},
        customer_id INTEGER,
        subscription_id INTEGER,
        shipping_date TEXT,
        courier TEXT,
        tracking_number TEXT,
        status TEXT,
        created_at TEXT
    )
    """)

    cur.execute(f"""
    CREATE TABLE IF NOT EXISTS payments (
        id {id_type},
        customer_id INTEGER,
        subscription_id INTEGER,
        amount INTEGER,
        payment_status TEXT,
        payment_date TEXT,
        payment_method TEXT,
        created_at TEXT
    )
    """)

    conn.commit()
    conn.close()