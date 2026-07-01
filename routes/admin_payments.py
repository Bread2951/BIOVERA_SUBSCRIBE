from flask import Blueprint, render_template, redirect, session
from database import get_db

payments_bp = Blueprint("payments_admin", __name__)


@payments_bp.route("/admin/payments")
def payment_list():
    if not session.get("logged_in"):
        return redirect("/login")

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT
            payments.id,
            customers.id,
            customers.name,
            customers.phone,
            subscriptions.plan,
            payments.amount,
            payments.payment_status,
            payments.payment_method,
            payments.payment_date,
            subscriptions.id,
            subscriptions.status
        FROM payments
        LEFT JOIN customers
        ON payments.customer_id = customers.id
        LEFT JOIN subscriptions
        ON payments.subscription_id = subscriptions.id
        ORDER BY payments.id DESC
    """)

    payments = cur.fetchall()
    conn.close()

    return render_template("admin/payments.html", payments=payments)