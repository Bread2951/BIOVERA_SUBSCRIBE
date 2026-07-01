from flask import Blueprint, render_template, redirect, session
from datetime import date
import calendar
from database import get_db

dashboard_bp = Blueprint("dashboard", __name__)


def update_due_shipments():
    today_text = date.today().strftime("%Y-%m-%d")

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        UPDATE subscriptions
        SET status = '결제완료'
        WHERE status = '배송대기'
          AND next_shipping_date <= ?
          AND remaining_count > 0
    """, (today_text,))

    conn.commit()
    conn.close()


@dashboard_bp.route("/admin")
def admin_dashboard():
    if not session.get("logged_in"):
        return redirect("/login")

    update_due_shipments()

    conn = get_db()
    cur = conn.cursor()

    today = date.today()
    today_text = today.strftime("%Y-%m-%d")
    tomorrow_text = date.fromordinal(today.toordinal() + 1).strftime("%Y-%m-%d")

    month_start = today.replace(day=1).strftime("%Y-%m-%d")
    month_end = today.replace(day=calendar.monthrange(today.year, today.month)[1]).strftime("%Y-%m-%d")

    cur.execute("""
        SELECT COUNT(*)
        FROM subscriptions
        WHERE next_shipping_date BETWEEN ? AND ?
    """, (month_start, month_end))
    monthly_shipping_count = cur.fetchone()[0]

    cur.execute("""
        SELECT COUNT(*)
        FROM subscriptions
        WHERE next_shipping_date = ?
          AND status IN ('결제완료', '배송준비')
    """, (today_text,))
    today_shipping_count = cur.fetchone()[0]

    cur.execute("""
        SELECT COUNT(*)
        FROM subscriptions
        WHERE next_shipping_date = ?
          AND status IN ('결제완료', '배송준비')
    """, (tomorrow_text,))
    tomorrow_shipping_count = cur.fetchone()[0]

    cur.execute("""
        SELECT COUNT(*)
        FROM subscriptions
        WHERE status = '입금대기'
    """)
    deposit_waiting_count = cur.fetchone()[0]

    cur.execute("""
        SELECT COUNT(*)
        FROM subscriptions
        WHERE status = '배송준비'
    """)
    shipping_ready_count = cur.fetchone()[0]

    cur.execute("""
        SELECT COUNT(*)
        FROM subscriptions
        WHERE status != '구독해지'
    """)
    active_subscription_count = cur.fetchone()[0]

    cur.execute("""
        SELECT customers.id, customers.name, customers.phone, subscriptions.plan, subscriptions.status, subscriptions.next_shipping_date
        FROM customers
        LEFT JOIN subscriptions
        ON customers.id = subscriptions.customer_id
        ORDER BY customers.id DESC
        LIMIT 5
    """)
    recent_customers = cur.fetchall()

    conn.close()

    return render_template(
        "admin/dashboard.html",
        monthly_shipping_count=monthly_shipping_count,
        today_shipping_count=today_shipping_count,
        tomorrow_shipping_count=tomorrow_shipping_count,
        deposit_waiting_count=deposit_waiting_count,
        shipping_ready_count=shipping_ready_count,
        active_subscription_count=active_subscription_count,
        recent_customers=recent_customers
    )