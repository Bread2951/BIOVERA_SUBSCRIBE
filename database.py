import sqlite3

DB_NAME = "customers.db"


def get_db():
    conn = sqlite3.connect(DB_NAME)
    return conn


def init_db():
    conn = get_db()
    cur = conn.cursor()

    # 고객 기본정보
    cur.execute("""
    CREATE TABLE IF NOT EXISTS customers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        phone TEXT,
        address TEXT,
        created_at TEXT
    )
    """)

    # 구독 정보
    cur.execute("""
    CREATE TABLE IF NOT EXISTS subscriptions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_id INTEGER,
        plan TEXT,
        start_date TEXT,
        memo TEXT,
        status TEXT,
        remaining_count INTEGER DEFAULT 12,
        next_shipping_date TEXT,
        created_at TEXT,
        FOREIGN KEY (customer_id) REFERENCES customers(id)
    )
    """)

    # 배송 정보
    cur.execute("""
    CREATE TABLE IF NOT EXISTS shipments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_id INTEGER,
        subscription_id INTEGER,
        shipping_date TEXT,
        courier TEXT,
        tracking_number TEXT,
        status TEXT,
        created_at TEXT,
        FOREIGN KEY (customer_id) REFERENCES customers(id),
        FOREIGN KEY (subscription_id) REFERENCES subscriptions(id)
    )
    """)

    # 결제 정보
    cur.execute("""
    CREATE TABLE IF NOT EXISTS payments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_id INTEGER,
        subscription_id INTEGER,
        amount INTEGER,
        payment_status TEXT,
        payment_date TEXT,
        payment_method TEXT,
        created_at TEXT,
        FOREIGN KEY (customer_id) REFERENCES customers(id),
        FOREIGN KEY (subscription_id) REFERENCES subscriptions(id)
    )
    """)

    conn.commit()
    conn.close()