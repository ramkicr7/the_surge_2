from extensions import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
import datetime


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)

    full_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(15), nullable=False)
    aadhaar = db.Column(db.String(12), nullable=False)

    password_hash = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), default="user")

    balance = db.Column(db.Float, default=100000.0)

    # 🔐 Secure TPIN (HASHED)
    tpin_hash = db.Column(db.String(200))

    # 🔐 OTP system
    otp_code = db.Column(db.String(6))
    otp_expiry = db.Column(db.DateTime)
    otp_attempts = db.Column(db.Integer, default=0)

    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    # Relationship with trades
    trades = db.relationship("Trade", backref="user", lazy=True)

    # ---------------- PASSWORD ---------------- #

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    # ---------------- TPIN ---------------- #

    def set_tpin(self, tpin):
        self.tpin_hash = generate_password_hash(tpin)

    def check_tpin(self, tpin):
        if not self.tpin_hash:
            return False
        return check_password_hash(self.tpin_hash, tpin)

    # ---------------- OTP ---------------- #

    def set_otp(self, otp):
        self.otp_code = otp
        self.otp_expiry = datetime.datetime.utcnow() + datetime.timedelta(minutes=5)
        self.otp_attempts = 0

    def verify_otp(self, otp):
        if not self.otp_code:
            return False

        if datetime.datetime.utcnow() > self.otp_expiry:
            return False

        if self.otp_attempts >= 3:
            return False

        if self.otp_code == otp:
            self.otp_code = None
            self.otp_expiry = None
            self.otp_attempts = 0
            return True
        else:
            self.otp_attempts += 1
            return False


class Trade(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    symbol = db.Column(db.String(20), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=False)

    trade_type = db.Column(db.String(10), nullable=False)  # BUY / SELL
    trade_mode = db.Column(db.String(20), default="DELIVERY")  # DELIVERY / SWING / INTRADAY

    leverage = db.Column(db.Float, default=1.0)

    stop_loss = db.Column(db.Float, nullable=True)
    target_price = db.Column(db.Float, nullable=True)

    status = db.Column(db.String(20), default="OPEN")  # OPEN / CLOSED

    total_amount = db.Column(db.Float)
    holding_days = db.Column(db.Integer, default=0)
    closed_at = db.Column(db.DateTime, nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    def calculate_total(self):
        self.total_amount = self.quantity * self.price * self.leverage