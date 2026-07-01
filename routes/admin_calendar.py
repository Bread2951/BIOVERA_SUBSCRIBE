from flask import Blueprint, render_template, request, redirect, session
from datetime import date
import calendar

from database import get_db

calendar_bp = Blueprint("calendar_admin", __name__)


@calendar_bp.route("/admin/calendar")
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


@calendar_bp.route("/admin/calendar/<shipping_date>")
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