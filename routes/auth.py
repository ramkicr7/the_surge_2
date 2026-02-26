from flask import Blueprint, render_template, redirect, request, flash, session, url_for
from flask_login import login_user, logout_user, login_required
from models import User
from extensions import db
from email_utils import send_email_async, generate_tpin, generate_otp

auth = Blueprint("auth", __name__)


# ================= REGISTER =================

@auth.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":

        # Create user
        user = User(
            full_name=request.form["full_name"],
            email=request.form["email"],
            phone=request.form["phone"],
            aadhaar=request.form["aadhaar"],
        )

        user.set_password(request.form["password"])

        # 🔐 Generate TPIN (4-digit)
        tpin = generate_tpin()
        user.set_tpin(tpin)

        db.session.add(user)
        db.session.commit()

        # 📩 Send TPIN Email (Background)
        send_email_async(
            user.email,
            "Welcome to THE SURGE - Your TPIN",
            f"Your TPIN is {tpin}. Keep it secure."
        )

        flash("Account created successfully. TPIN sent to your email.", "success")
        return redirect(url_for("auth.login"))

    return render_template("register.html")


# ================= LOGIN (STEP 1 - PASSWORD CHECK) =================

@auth.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":

        user = User.query.filter_by(email=request.form["email"]).first()

        if user and user.check_password(request.form["password"]):

            # 🔐 Generate OTP
            otp = generate_otp()
            user.set_otp(otp)
            db.session.commit()

            # 📩 Send OTP Email
            send_email_async(
                user.email,
                "Login OTP - THE SURGE",
                f"Your login OTP is {otp}"
            )

            # Store user temporarily
            session["temp_user_id"] = user.id

            return redirect(url_for("auth.verify_login_otp"))

        flash("Invalid credentials", "danger")

    return render_template("login.html")


# ================= LOGIN (STEP 2 - OTP VERIFY) =================

@auth.route("/verify-login-otp", methods=["GET", "POST"])
def verify_login_otp():

    if request.method == "POST":

        user_id = session.get("temp_user_id")

        if not user_id:
            flash("Session expired. Login again.", "danger")
            return redirect(url_for("auth.login"))

        user = User.query.get(user_id)

        entered_otp = request.form["otp"]

        if user.verify_otp(entered_otp):

            db.session.commit()

            login_user(user)

            session.pop("temp_user_id", None)

            return redirect("/dashboard")

        else:
            db.session.commit()
            flash("Invalid or expired OTP", "danger")

    return render_template("otp_verify.html")


# ================= LOGOUT =================

@auth.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect("/")