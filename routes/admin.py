from flask import Blueprint, render_template, request, redirect, session, Response
import csv
import io
from datetime import date, datetime
import calendar
from database import get_db

admin_bp = Blueprint("admin", __name__)
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


@admin_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        if username == "admin" and password == "1234":
            session["logged_in"] = True
            return redirect("/admin")

        return render_template("admin/login.html", error="아이디 또는 비밀번호가 틀렸습니다.")

    return render_template("admin/login.html")


@admin_bp.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


@admin_bp.route("/admin")
def admin_dashboard():
    if not session.get("logged_in"):
        return redirect("/login")

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

@admin_bp.route("/customer/<int:customer_id>")
def customer_detail(customer_id):
    if not session.get("logged_in"):
        return redirect("/login")

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
        WHERE customers.id = ?
    """, (customer_id,))
    customer = cur.fetchone()

    cur.execute("""
        SELECT amount, payment_status, payment_date, payment_method
        FROM payments
        WHERE customer_id = ?
        ORDER BY id DESC
    """, (customer_id,))
    payments = cur.fetchall()

    cur.execute("""
        SELECT shipping_date, courier, tracking_number, status, created_at
        FROM shipments
        WHERE customer_id = ?
        ORDER BY id DESC
    """, (customer_id,))
    shipments = cur.fetchall()

    conn.close()

    return render_template(
        "admin/customer_detail.html",
        customer=customer,
        payments=payments,
        shipments=shipments
    )

@admin_bp.route("/edit/<int:customer_id>", methods=["GET", "POST"])
def edit_customer(customer_id):
    if not session.get("logged_in"):
        return redirect("/login")

    conn = get_db()
    cur = conn.cursor()

    if request.method == "POST":
        name = request.form["name"]
        phone = request.form["phone"]
        address = request.form["address"]
        plan = request.form["plan"]
        start_date = request.form["start_date"]
        memo = request.form.get("memo", "")
        status = request.form["status"]

        cur.execute("""
            UPDATE customers
            SET name = ?, phone = ?, address = ?
            WHERE id = ?
        """, (name, phone, address, customer_id))

        cur.execute("""
            UPDATE subscriptions
            SET plan = ?, start_date = ?, memo = ?, status = ?, next_shipping_date = ?
            WHERE customer_id = ?
        """, (plan, start_date, memo, status, start_date, customer_id))

        conn.commit()
        conn.close()

        return redirect("/admin")

    cur.execute("""
        SELECT
            customers.id,
            customers.name,
            customers.phone,
            customers.address,
            subscriptions.plan,
            subscriptions.start_date,
            subscriptions.memo,
            subscriptions.status
        FROM customers
        LEFT JOIN subscriptions
        ON customers.id = subscriptions.customer_id
        WHERE customers.id = ?
    """, (customer_id,))

    customer = cur.fetchone()
    conn.close()

    return render_template("admin/edit.html", customer=customer)


@admin_bp.route("/delete/<int:customer_id>")
def delete_customer(customer_id):
    if not session.get("logged_in"):
        return redirect("/login")

    conn = get_db()
    cur = conn.cursor()

    cur.execute("DELETE FROM payments WHERE customer_id = ?", (customer_id,))
    cur.execute("DELETE FROM shipments WHERE customer_id = ?", (customer_id,))
    cur.execute("DELETE FROM subscriptions WHERE customer_id = ?", (customer_id,))
    cur.execute("DELETE FROM customers WHERE id = ?", (customer_id,))

    conn.commit()
    conn.close()

    return redirect("/admin")

@admin_bp.route("/admin/shipments")
def shipment_list():
    if not session.get("logged_in"):
        return redirect("/login")
        tracking_number = request.form["tracking_number"]

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
        WHERE subscriptions.status IN ('입금대기','결제완료', '배송준비')
        ORDER BY subscriptions.next_shipping_date ASC
    """)

    shipments = cur.fetchall()
    conn.close()

    return render_template("admin/shipments.html", shipments=shipments)

@admin_bp.route("/shipment-ready/<int:subscription_id>")
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

@admin_bp.route("/shipment-complete/<int:subscription_id>", methods=["POST"])
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
            VALUES (?, ?, ?, ?, ?, ?, DATE('now'))
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

@admin_bp.route("/payment-confirm/<int:subscription_id>")
def payment_confirm(subscription_id):

    if not session.get("logged_in"):
        return redirect("/login")

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        UPDATE subscriptions
        SET status='결제완료'
        WHERE id=?
    """,(subscription_id,))

    cur.execute("""
        UPDATE payments
        SET payment_status='결제완료'
        WHERE subscription_id=?
    """,(subscription_id,))

    conn.commit()
    conn.close()

    return redirect("/admin/shipments")

@admin_bp.route("/admin/shipments/export")
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
    output.write('\ufeff')
    writer = csv.writer(output)

    writer.writerow(["이름", "연락처", "주소", "상품", "다음배송일", "요청사항", "상태"])

    for row in rows:
        writer.writerow(row)

    response = Response(output.getvalue(), mimetype="text/csv")
    response.headers["Content-Disposition"] = "attachment; filename=shipments.csv"

    return response

@admin_bp.route("/admin/customers")
def customer_list():
    if not session.get("logged_in"):
        return redirect("/login")

    conn = get_db()
    cur = conn.cursor()

    search = request.args.get("search", "")
    status = request.args.get("status", "")

    base_query = """
        SELECT
            customers.id,
            customers.name,
            customers.phone,
            customers.address,
            subscriptions.plan,
            subscriptions.status,
            subscriptions.remaining_count,
            subscriptions.next_shipping_date
        FROM customers
        LEFT JOIN subscriptions
        ON customers.id = subscriptions.customer_id
    """

    conditions = []
    params = []

    if search:
        conditions.append("""
            (customers.name LIKE ?
             OR customers.phone LIKE ?
             OR customers.address LIKE ?
             OR subscriptions.plan LIKE ?)
        """)
        params.extend([f"%{search}%", f"%{search}%", f"%{search}%", f"%{search}%"])

    if status:
        conditions.append("subscriptions.status = ?")
        params.append(status)

    where_sql = ""
    if conditions:
        where_sql = " WHERE " + " AND ".join(conditions)

    cur.execute(base_query + where_sql + """
        ORDER BY customers.id DESC
    """, params)

    customers = cur.fetchall()
    conn.close()

    return render_template(
        "admin/customers.html",
        customers=customers,
        search=search,
        status=status
    )

@admin_bp.route("/admin/payments")
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

@admin_bp.route("/admin/calendar")
def shipping_calendar():
    if not session.get("logged_in"):
        return redirect("/login")

    today = date.today()
    year = int(request.args.get("year", today.year))
    month = int(request.args.get("month", today.month))

    first_day = date(year, month, 1)
    last_day_num = calendar.monthrange(year, month)[1]
    last_day = date(year, month, last_day_num)

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT next_shipping_date, COUNT(*)
        FROM subscriptions
        WHERE next_shipping_date BETWEEN ? AND ?
          AND status IN ('결제완료', '배송준비', '배송대기')
        GROUP BY next_shipping_date
    """, (first_day.strftime("%Y-%m-%d"), last_day.strftime("%Y-%m-%d")))

    rows = cur.fetchall()
    conn.close()

    shipping_counts = {}
    for r in rows:
        shipping_counts[r[0]] = r[1]

    cal = calendar.Calendar(firstweekday=0)
    weeks = cal.monthdatescalendar(year, month)

    prev_month = month - 1
    prev_year = year
    if prev_month == 0:
        prev_month = 12
        prev_year -= 1

    next_month = month + 1
    next_year = year
    if next_month == 13:
        next_month = 1
        next_year += 1

    return render_template(
        "admin/calendar.html",
        year=year,
        month=month,
        weeks=weeks,
        shipping_counts=shipping_counts,
        prev_year=prev_year,
        prev_month=prev_month,
        next_year=next_year,
        next_month=next_month,
        today=today.strftime("%Y-%m-%d")
    )

@admin_bp.route("/admin/calendar/<shipping_date>")
def calendar_day_detail(shipping_date):
    if not session.get("logged_in"):
        return redirect("/login")

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
            subscriptions.status,
            subscriptions.remaining_count,
            subscriptions.next_shipping_date
        FROM customers
        LEFT JOIN subscriptions
        ON customers.id = subscriptions.customer_id
        WHERE subscriptions.next_shipping_date = ?
        ORDER BY customers.id DESC
    """, (shipping_date,))

    customers = cur.fetchall()
    conn.close()

    return render_template(
        "admin/calendar_day.html",
        shipping_date=shipping_date,
        customers=customers
    )