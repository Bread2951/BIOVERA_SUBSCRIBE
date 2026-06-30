from flask import Blueprint, render_template, request
from datetime import date
from database import get_db

customer_bp = Blueprint("customer", __name__)


def get_amount(plan):
    if plan == "500ml 15병 월구독":
        return 680000
    elif plan == "500ml 30병 월구독":
        return 990000
    return 0


@customer_bp.route("/subscribe", methods=["GET", "POST"])
def subscribe():
    if request.method == "POST":
        name = request.form["name"]
        phone = request.form["phone"]
        address = request.form["address"]
        detail_address = request.form["detail_address"]
        plan = request.form["plan"]
        start_date = request.form["start_date"]
        memo = request.form.get("memo", "")

        amount = get_amount(plan)

        return render_template(
            "customer/payment.html",
            name=name,
            phone=phone,
            address=address,
            detail_address=detail_address,
            plan=plan,
            start_date=start_date,
            memo=memo,
            amount=amount
        )

    return render_template("customer/subscribe.html")


@customer_bp.route("/payment-complete", methods=["POST"])
def payment_complete():
    name = request.form["name"]
    phone = request.form["phone"]
    address = request.form["address"]
    detail_address = request.form.get("detail_address", "")
    address = address + " " + detail_address
    plan = request.form["plan"]
    start_date = request.form["start_date"]
    memo = request.form.get("memo", "")
    amount = request.form["amount"]
    payment_method = request.form.get("payment_method", "무통장입금")

    today = date.today().strftime("%Y-%m-%d")

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO customers
        (name, phone, address, created_at)
        VALUES (?, ?, ?, ?)
    """, (name, phone, address, today))

    customer_id = cur.lastrowid

    cur.execute("""
        INSERT INTO subscriptions
        (customer_id, plan, start_date, memo, status, remaining_count, next_shipping_date, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        customer_id,
        plan,
        start_date,
        memo,
        "입금대기",
        12,
        start_date,
        today
    ))

    subscription_id = cur.lastrowid

    cur.execute("""
        INSERT INTO payments
        (customer_id, subscription_id, amount, payment_status, payment_date, payment_method, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        customer_id,
        subscription_id,
        amount,
        "입금대기",
today,
payment_method,
today
    ))

    conn.commit()
    conn.close()

    return render_template("customer/complete.html", name=name)

@customer_bp.route("/mypage", methods=["GET", "POST"])
def mypage():
    customer = None

    if request.method == "POST":
        phone = request.form["phone"]

        conn = get_db()
        cur = conn.cursor()

        cur.execute("""
            SELECT
                customers.id,
                customers.name,
                customers.phone,
                customers.address,
                customers.created_at,
                subscriptions.id,
                subscriptions.plan,
                subscriptions.start_date,
                subscriptions.memo,
                subscriptions.status,
                subscriptions.remaining_count,
                subscriptions.next_shipping_date
            FROM customers
            LEFT JOIN subscriptions
            ON customers.id = subscriptions.customer_id
            WHERE customers.phone = ?
            ORDER BY customers.id DESC
            LIMIT 1
        """, (phone,))

        customer = cur.fetchone()
        conn.close()

    return render_template("customer/mypage.html", customer=customer)