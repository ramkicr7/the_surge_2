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
    tpin = db.Column(db.String(4))
    otp_verified = db.Column(db.Boolean, default=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Trade(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    symbol = db.Column(db.String(20))
    quantity = db.Column(db.Integer)
    price = db.Column(db.Float)
    trade_type = db.Column(db.String(10))  # BUY or SELL
    timestamp = db.Column(db.DateTime, default=datetime.datetime.utcnow)