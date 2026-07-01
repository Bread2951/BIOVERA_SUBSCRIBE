from flask import Flask, redirect
from database import init_db

from routes.auth import auth_bp
from routes.admin_dashboard import dashboard_bp
from routes.admin_customers import customers_bp
from routes.admin_payments import payments_bp
from routes.admin_shipments import shipments_bp
from routes.admin_calendar import calendar_bp
from routes.customer import customer_bp

app = Flask(__name__)
app.secret_key = "biovvera_secret_key"

init_db()

app.register_blueprint(auth_bp)
app.register_blueprint(dashboard_bp)
app.register_blueprint(customers_bp)
app.register_blueprint(payments_bp)
app.register_blueprint(shipments_bp)
app.register_blueprint(calendar_bp)
app.register_blueprint(customer_bp)


@app.route("/")
def home():
    return redirect("/subscribe")


if __name__ == "__main__":
    app.run(debug=True)