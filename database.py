import os
import sqlite3
import psycopg2
import dj_database_url

DATABASE_URL = os.environ.get("DATABASE_URL")
DB_NAME = "customers.db"


def get_db():
    if DATABASE_URL:
        return psycopg2.connect(DATABASE_URL)
    else:
        return sqlite3.connect(DB_NAME)


def init_db():
    conn = get_db()
    cur = conn.cursor()

    if DATABASE_URL:
        id_type = "SERIAL PRIMARY KEY"
        text_type = "TEXT"
        integer_type = "INTEGER"
    else:
        id_type = "INTEGER PRIMARY KEY AUTOINCREMENT"
        text_type = "TEXT"
        integer_type = "INTEGER"

    cur.execute(f"""
    CREATE TABLE IF NOT EXISTS customers (
        id {id_type},
        name {text_type} NOT NULL,
        phone {text_type},
        address {text_type},
        created_at {text_type}
    )
    """)

    cur.execute(f"""
    CREATE TABLE IF NOT EXISTS subscriptions (
        id {id_type},
        customer_id {integer_type},
        plan {text_type},
        start_date {text_type},
        memo {text_type},
        status {text_type},
        remaining_count {integer_type} DEFAULT 12,
        next_shipping_date {text_type},
        created_at {text_type}
    )
    """)

    cur.execute(f"""
    CREATE TABLE IF NOT EXISTS shipments (
        id {id_type},
        customer_id {integer_type},
        subscription_id {integer_type},
        shipping_date {text_type},
        courier {text_type},
        tracking_number {text_type},
        status {text_type},
        created_at {text_type}
    )
    """)

    cur.execute(f"""
    CREATE TABLE IF NOT EXISTS payments (
        id {id_type},
        customer_id {integer_type},
        subscription_id {integer_type},
        amount {integer_type},
        payment_status {text_type},
        payment_date {text_type},
        payment_method {text_type},
        created_at {text_type}
    )
    """)

    conn.commit()
    conn.close()