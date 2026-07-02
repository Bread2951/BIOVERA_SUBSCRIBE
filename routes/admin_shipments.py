from flask import Blueprint, render_template, request, redirect, session, Response
from datetime import date, datetime
import calendar
import csv
import io

from database import get_db

shipments_bp = Blueprint("shipments_admin", __name__)


def add_one_month(date_text):
    current_date = datetime.strptime(date_text, "%Y-%m-%d").date()

    year = current_date.year
    month = current_date.month + 1

    if month > 12:
        month = 1
        year += 1

    last_day = calendar.monthrange(year, month)[1]
    day = min(current_date.day, last_day)

    next_date = date(year, month, day)
    return next_date.strftime("%Y-%m-%d")


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


@shipments_bp.route("/admin/shipments")
def shipment_list():
    if not session.get("logged_in"):
        return redirect("/login")

    update_due_shipments()

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT
            customers.id,
            customers.name,
            customers.phone,
            customers.address,
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
        WHERE subscriptions.status IN ('입금대기', '결제완료', '배송준비')
        ORDER BY subscriptions.next_shipping_date ASC
    """)

    shipments = cur.fetchall()
    conn.close()

    return render_template("admin/shipments.html", shipments=shipments)


@shipments_bp.route("/shipment-ready/<int:subscription_id>")
def shipment_ready(subscription_id):
    if not session.get("logged_in"):
        return redirect("/login")

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        UPDATE subscriptions
        SET status = '배송준비'
        WHERE id = ?
    """, (subscription_id,))

    conn.commit()
    conn.close()

    return redirect("/admin/shipments")


@shipments_bp.route("/shipment-complete/<int:subscription_id>", methods=["POST"])
def shipment_complete(subscription_id):
    if not session.get("logged_in"):
        return redirect("/login")

    tracking_number = request.form["tracking_number"]
    courier = request.form["courier"]

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT customer_id, next_shipping_date, remaining_count
        FROM subscriptions
        WHERE id = ?
    """, (subscription_id,))
    subscription = cur.fetchone()

    if subscription:
        customer_id = subscription[0]
        shipping_date = subscription[1]
        remaining_count = subscription[2] or 0

        new_remaining_count = max(remaining_count - 1, 0)
        next_shipping_date = add_one_month(shipping_date)

        cur.execute("""
            INSERT INTO shipments
            (customer_id, subscription_id, shipping_date, courier, tracking_number, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, CURRENT_DATE)
        """, (
            customer_id,
            subscription_id,
            shipping_date,
            courier,
            tracking_number,
            "배송완료"
        ))

        cur.execute("""
            UPDATE subscriptions
            SET status = '배송대기',
                remaining_count = ?,
                next_shipping_date = ?
            WHERE id = ?
        """, (new_remaining_count, next_shipping_date, subscription_id))

    conn.commit()
    conn.close()

    return redirect("/admin/shipments")


@shipments_bp.route("/payment-confirm/<int:subscription_id>")
def payment_confirm(subscription_id):
    if not session.get("logged_in"):
        return redirect("/login")

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        UPDATE subscriptions
        SET status = '결제완료'
        WHERE id = ?
    """, (subscription_id,))

    cur.execute("""
        UPDATE payments
        SET payment_status = '결제완료'
        WHERE subscription_id = ?
    """, (subscription_id,))

    conn.commit()
    conn.close()

    return redirect("/admin/shipments")


@shipments_bp.route("/admin/shipments/export")
def export_shipments():
    if not session.get("logged_in"):
        return redirect("/login")

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT
            customers.name,
            customers.phone,
            customers.address,
            subscriptions.plan,
            subscriptions.next_shipping_date,
            subscriptions.memo,
            subscriptions.status
        FROM customers
        LEFT JOIN subscriptions
        ON customers.id = subscriptions.customer_id
        WHERE subscriptions.status IN ('결제완료', '배송준비')
        ORDER BY subscriptions.next_shipping_date ASC
    """)

    rows = cur.fetchall()
    conn.close()

    output = io.StringIO()
    output.write("\ufeff")
    writer = csv.writer(output)

    writer.writerow(["이름", "연락처", "주소", "상품", "다음배송일", "요청사항", "상태"])

    for row in rows:
        writer.writerow(row)

    response = Response(output.getvalue(), mimetype="text/csv")
    response.headers["Content-Disposition"] = "attachment; filename=shipments.csv"

    return response

@shipments_bp.route("/pickup-complete/<int:subscription_id>")
def pickup_complete(subscription_id):
    if not session.get("logged_in"):
        return redirect("/login")

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT customer_id, next_shipping_date, remaining_count
        FROM subscriptions
        WHERE id = ?
    """, (subscription_id,))
    subscription = cur.fetchone()

    if subscription:
        customer_id = subscription[0]
        shipping_date = subscription[1]
        remaining_count = subscription[2] or 0

        new_remaining_count = max(remaining_count - 1, 0)
        next_shipping_date = add_one_month(shipping_date)

        cur.execute("""
            INSERT INTO shipments
            (customer_id, subscription_id, shipping_date, courier, tracking_number, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, CURRENT_DATE)
        """, (
            customer_id,
            subscription_id,
            shipping_date,
            "직접수령",
            "",
            "직접수령완료"
        ))

        cur.execute("""
            UPDATE subscriptions
            SET status = '배송대기',
                remaining_count = ?,
                next_shipping_date = ?
            WHERE id = ?
        """, (new_remaining_count, next_shipping_date, subscription_id))

    conn.commit()
    conn.close()

    return redirect("/admin/shipments")