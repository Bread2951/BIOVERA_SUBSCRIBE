from flask import Flask, redirect
from database import init_db
from routes.admin import admin_bp
from routes.customer import customer_bp

app = Flask(__name__)
app.secret_key = "biovvera_secret_key"

# Render에서도 DB 테이블 생성되게 실행
init_db()

app.register_blueprint(admin_bp)
app.register_blueprint(customer_bp)


@app.route("/")
def home():
    return redirect("/subscribe")


if __name__ == "__main__":
    app.run(debug=True)