from flask import Flask, redirect
from database import init_db
from routes.admin import admin_bp
from routes.customer import customer_bp

app = Flask(__name__)
app.secret_key = "biovvera_secret_key"

# 관리자
app.register_blueprint(admin_bp)

# 고객
app.register_blueprint(customer_bp)


@app.route("/")
def home():
    return redirect("/subscribe")


if __name__ == "__main__":
    init_db()
    app.run(debug=True)