from flask import Blueprint, render_template, redirect, request, flash
from models import User
from extensions import db
from flask_login import login_user, logout_user, login_required
import random

auth = Blueprint("auth", __name__)

@auth.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        user = User(
            full_name=request.form["full_name"],
            email=request.form["email"],
            phone=request.form["phone"],
            aadhaar=request.form["aadhaar"],
        )
        user.set_password(request.form["password"])
        user.tpin = str(random.randint(1000,9999))
        db.session.add(user)
        db.session.commit()

        flash(f"Account created. Your T-PIN is {user.tpin}")
        return redirect("/login")

    return render_template("register.html")


@auth.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = User.query.filter_by(email=request.form["email"]).first()
        if user and user.check_password(request.form["password"]):
            login_user(user)
            return redirect("/dashboard")
        flash("Invalid credentials")

    return render_template("login.html")


@auth.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect("/")