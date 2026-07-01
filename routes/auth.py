from flask import Blueprint, render_template, request, redirect, session

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        if username == "admin" and password == "1234":
            session["logged_in"] = True
            return redirect("/admin")

        return render_template("admin/login.html", error="아이디 또는 비밀번호가 틀렸습니다.")

    return render_template("admin/login.html")


@auth_bp.route("/logout")
def logout():
    session.clear()
    return redirect("/login")