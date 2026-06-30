from flask import Blueprint, render_template, request, redirect, session
from datetime import date
from database import get_db

admin_bp = Blueprint("admin", __name__)


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

    search = request.args.get("search", "")

    base_query = """
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
    """

    if search:
        cur.execute(base_query + """
            WHERE customers.name LIKE ?
               OR customers.phone LIKE ?
               OR customers.address LIKE ?
               OR subscriptions.plan LIKE ?
            ORDER BY customers.id DESC
        """, (f"%{search}%", f"%{search}%", f"%{search}%", f"%{search}%"))
    else:
        cur.execute(base_query + """
            ORDER BY customers.id DESC
        """)

    customers = cur.fetchall()
    conn.close()

    total_count = len(customers)
    new_count = len([c for c in customers if c[7] == "결제완료"])
    today = date.today().strftime("%Y-%m-%d")
    today_count = len([c for c in customers if c[5] == today])

    shipping_ready_count = len([c for c in customers if c[7] == "결제완료"])
    shipping_progress_count = len([c for c in customers if c[7] == "배송준비"])
    waiting_count = len([c for c in customers if c[7] == "배송대기"])

    return render_template(
        "admin/dashboard.html",
        customers=customers,
        total_count=total_count,
        new_count=new_count,
        today_count=today_count,
        search=search,
        shipping_ready_count=shipping_ready_count,
        shipping_progress_count=shipping_progress_count,
        waiting_count=waiting_count
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
        WHERE subscriptions.status IN ('결제완료', '배송준비')
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
                next_shipping_date = DATE(next_shipping_date, '+30 days')
            WHERE id = ?
        """, (new_remaining_count, subscription_id))

    conn.commit()
    conn.close()

    return redirect("/admin/shipments")