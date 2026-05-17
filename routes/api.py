from flask import Blueprint, request, jsonify
from models import Trade, User
from extensions import db

api = Blueprint("api", __name__)

API_KEY = "my_super_secret_123"

@api.route("/receive-trade", methods=["POST"])
def receive_trade():

    # 🔐 API SECURITY
    if request.headers.get("X-API-KEY") != API_KEY:
        return jsonify({"error": "Unauthorized"}), 403

    data = request.json

    print("\n📥 AI TRADE RECEIVED")
    print(data)

    ticker = data.get("ticker")
    price = data.get("market_price")
    qty = data.get("position_size")

    if not ticker or not price or not qty:
        return jsonify({"error": "Missing fields"}), 400

    # 🔎 Determine strategy
    strategy = "DELIVERY"

    if data["intraday_strategy"]["signal"] == "BUY":
        strategy = "INTRADAY"
    elif data["swing_strategy"]["signal"] == "BUY":
        strategy = "SWING"
    elif data["long_term_strategy"]["signal"] == "BUY":
        strategy = "DELIVERY"

    # 👤 select first user
    user = User.query.first()

    if not user:
        return jsonify({"error": "No user found"}), 400

    leverage = 1

    if strategy == "INTRADAY":
        leverage = 5
        required_amount = (price * qty) / leverage
    else:
        required_amount = price * qty

    if user.balance < required_amount:
        return jsonify({"error": "Insufficient balance"}), 400

    # 💰 deduct balance
    user.balance -= required_amount

    stop_loss_percent = data["risk_management"].get("stop_loss_percent", 0)

    stop_loss = None
    if stop_loss_percent:
        stop_loss = price * (1 - stop_loss_percent / 100)

    trade = Trade(
        user_id=user.id,
        symbol=ticker,
        quantity=qty,
        price=price,
        trade_type="BUY",
        trade_mode=strategy,
        leverage=leverage,
        stop_loss=stop_loss,
        target_price=None,
        status="OPEN"
    )

    trade.calculate_total()

    db.session.add(trade)
    db.session.commit()

    return jsonify({
        "status": "AI Trade Executed",
        "symbol": ticker,
        "mode": strategy
    })