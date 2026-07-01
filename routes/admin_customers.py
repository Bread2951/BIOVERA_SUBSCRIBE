from flask import Blueprint, render_template, request, redirect, session
from database import get_db

customers_bp = Blueprint("customers_admin", __name__)


@customers_bp.route("/customer/<int:customer_id>")
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


@customers_bp.route("/admin/customers")
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


@customers_bp.route("/edit/<int:customer_id>", methods=["GET", "POST"])
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

        return redirect("/admin/customers")

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


@customers_bp.route("/delete/<int:customer_id>")
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

    return redirect("/admin/customers")