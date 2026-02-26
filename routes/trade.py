from flask import Blueprint, redirect, flash, request, session, render_template, url_for
from flask_login import login_required, current_user
from models import Trade
from extensions import db
from email_utils import generate_otp, send_email_async
import yfinance as yf

trade = Blueprint("trade", __name__)


# ---------------- SAFE PRICE FETCH FUNCTION ----------------

def get_live_price(symbol):
    try:
        ticker = yf.Ticker(symbol)
        data = ticker.history(period="1d")

        if data is None or data.empty:
            return None

        return float(data["Close"].iloc[-1])

    except Exception as e:
        print("Price Fetch Error:", e)
        return None


# ================= BUY STOCK (STEP 1: TPIN + OTP) =================

@trade.route("/buy/<symbol>", methods=["POST"])
@login_required
def buy(symbol):

    quantity = int(request.form.get("quantity", 1))
    entered_tpin = request.form.get("tpin")
    trade_mode = request.form.get("trade_mode", "DELIVERY")
    stop_loss = request.form.get("stop_loss")
    target_price = request.form.get("target_price")

    if quantity <= 0:
        flash("Invalid quantity", "danger")
        return redirect(url_for("dashboard.dashboard_page"))

    if not current_user.check_tpin(entered_tpin):
        flash("Invalid TPIN", "danger")
        return redirect(url_for("dashboard.dashboard_page"))

    price = get_live_price(symbol)

    if not price:
        flash("Market data unavailable", "danger")
        return redirect(url_for("dashboard.dashboard_page"))

    # 🔥 Leverage Logic
    leverage = 1.0
    if trade_mode == "INTRADAY":
        leverage = 5.0
        required_amount = (price * quantity) / leverage
    else:
        required_amount = price * quantity

    if current_user.balance < required_amount:
        flash("Insufficient balance", "danger")
        return redirect(url_for("dashboard.dashboard_page"))

    # 🔐 Generate OTP
    otp = generate_otp()
    current_user.set_otp(otp)
    db.session.commit()

    send_email_async(
        current_user.email,
        "Trade OTP - THE SURGE",
        f"Your OTP to BUY {symbol} is {otp}"
    )

    # Store everything in session
    session["pending_trade"] = {
        "symbol": symbol,
        "quantity": quantity,
        "price": price,
        "type": "BUY",
        "mode": trade_mode,
        "stop_loss": float(stop_loss) if stop_loss else None,
        "target_price": float(target_price) if target_price else None,
        "leverage": leverage,
        "required_amount": required_amount
    }

    return redirect(url_for("trade.verify_trade_otp"))

# ================= SELL STOCK (STEP 1: TPIN + OTP) =================

@trade.route("/sell/<symbol>", methods=["POST"])
@login_required
def sell(symbol):

    quantity = int(request.form.get("quantity", 1))
    entered_tpin = request.form.get("tpin")

    if quantity <= 0:
        flash("Invalid quantity", "danger")
        return redirect(url_for("dashboard.portfolio"))

    if not current_user.check_tpin(entered_tpin):
        flash("Invalid TPIN", "danger")
        return redirect(url_for("dashboard.portfolio"))

    price = get_live_price(symbol)

    if price is None:
        flash("Market data unavailable. Try again.", "danger")
        return redirect(url_for("dashboard.portfolio"))

    # 🔥 FIX: Only count DELIVERY + SWING holdings
    buys = Trade.query.filter(
        Trade.user_id == current_user.id,
        Trade.symbol == symbol,
        Trade.trade_type == "BUY",
        Trade.trade_mode.in_(["DELIVERY", "SWING"])
    ).all()

    sells = Trade.query.filter(
        Trade.user_id == current_user.id,
        Trade.symbol == symbol,
        Trade.trade_type == "SELL",
        Trade.trade_mode.in_(["DELIVERY", "SWING"])
    ).all()

    total_bought = sum(t.quantity for t in buys)
    total_sold = sum(t.quantity for t in sells)

    holdings = total_bought - total_sold

    if holdings < quantity:
        flash("Not enough holdings to sell", "danger")
        return redirect(url_for("dashboard.portfolio"))

    otp = generate_otp()
    current_user.set_otp(otp)
    db.session.commit()

    send_email_async(
        current_user.email,
        "Trade OTP - THE SURGE",
        f"Your OTP to SELL {symbol} is {otp}"
    )

    session["pending_trade"] = {
        "symbol": symbol,
        "quantity": quantity,
        "price": price,
        "type": "SELL",
        "mode": "DELIVERY"
    }

    return redirect(url_for("trade.verify_trade_otp"))


# ================= OTP VERIFICATION =================
@trade.route("/verify-trade-otp", methods=["GET", "POST"])
@login_required
def verify_trade_otp():

    if request.method == "POST":

        entered_otp = request.form.get("otp")

        if current_user.verify_otp(entered_otp):

            trade_data = session.get("pending_trade")

            if not trade_data:
                flash("No trade pending", "danger")
                return redirect(url_for("dashboard.dashboard_page"))

            symbol = trade_data["symbol"]
            quantity = trade_data["quantity"]
            price = trade_data["price"]
            trade_type = trade_data["type"]
            trade_mode = trade_data["mode"]
            leverage = trade_data.get("leverage", 1.0)
            stop_loss = trade_data.get("stop_loss")
            target_price = trade_data.get("target_price")
            required_amount = trade_data.get("required_amount", price * quantity)

            # 🔥 BALANCE LOGIC
            if trade_type == "BUY":
                current_user.balance -= required_amount
            else:
                current_user.balance += required_amount

            # 🔥 CREATE TRADE
            new_trade = Trade(
                user_id=current_user.id,
                symbol=symbol,
                quantity=quantity,
                price=price,
                trade_type=trade_type,
                trade_mode=trade_mode,
                leverage=leverage,
                stop_loss=stop_loss,
                target_price=target_price,
                status="OPEN"
            )

            new_trade.calculate_total()
            db.session.add(new_trade)

            # 🔥 INTRADAY CLOSE LOGIC
            if trade_mode == "INTRADAY" and trade_type == "SELL":

                intraday_buys = Trade.query.filter_by(
                    user_id=current_user.id,
                    symbol=symbol,
                    trade_mode="INTRADAY",
                    trade_type="BUY",
                    status="OPEN"
                ).all()

                remaining = quantity

                for buy_trade in intraday_buys:
                    if remaining <= 0:
                        break

                    if buy_trade.quantity <= remaining:
                        buy_trade.status = "CLOSED"
                        remaining -= buy_trade.quantity
                    else:
                        buy_trade.quantity -= remaining
                        remaining = 0

            db.session.commit()

            # 📧 SUCCESS EMAIL
            send_email_async(
                current_user.email,
                "Trade Successful - THE SURGE",
                f"{symbol} {trade_type} ({quantity}) at ₹{round(price,2)} via {trade_mode}"
            )

            session.pop("pending_trade", None)

            flash(f"{symbol} {trade_type} successful ({trade_mode})!", "success")

            if trade_type == "BUY":
                return redirect(url_for("dashboard.dashboard_page"))
            else:
                return redirect(url_for("dashboard.portfolio"))

        else:
            flash("Invalid or Expired OTP", "danger")

    return render_template("otp_verify.html")
# ================= AI TRADE EXECUTION =================
# ================= AI TRADE EXECUTION =================
import os
from dotenv import load_dotenv

load_dotenv()

@trade.route("/receive-trade", methods=["POST"])
def receive_trade():

    data = request.get_json()

    if not data:
        return {"error": "No JSON received"}, 400

    # 🔐 Secure API key from .env
    API_KEY = os.getenv("AI_SECRET_KEY")

    if request.headers.get("X-API-KEY") != API_KEY:
        return {"error": "Unauthorized"}, 403

    ticker = data.get("ticker")
    market_price = data.get("market_price")
    qty = data.get("position_size")

    if not ticker or not market_price or not qty:
        return {"error": "Missing trade data"}, 400

    # 🔥 Decide Strategy Priority
    strategy = None

    if data.get("intraday_strategy", {}).get("action") == "BUY":
        strategy = "INTRADAY"
    elif data.get("swing_strategy", {}).get("action") == "BUY":
        strategy = "SWING"
    elif data.get("long_term_strategy", {}).get("action") == "BUY":
        strategy = "DELIVERY"

    if not strategy:
        return {"message": "No BUY signal from AI"}, 200

    # 🔥 Select user (you can change this later)
    from models import User
    user = User.query.first()

    if not user:
        return {"error": "No user found"}, 400

    # 🔥 Leverage logic (same as manual)
    leverage = 1.0
    if strategy == "INTRADAY":
        leverage = 5.0
        required_amount = (market_price * qty) / leverage
    else:
        required_amount = market_price * qty

    if user.balance < required_amount:
        return {"error": "Insufficient balance"}, 400

    # 🔥 Deduct balance
    user.balance -= required_amount

    # 🔥 Stop Loss from AI
    stop_loss_percent = data.get("risk_management", {}).get("stop_loss_percent", 0)
    stop_loss_value = None

    if stop_loss_percent:
        stop_loss_value = market_price * (1 - stop_loss_percent / 100)

    # 🔥 Create Trade (NO OTP / NO TPIN for AI)
    new_trade = Trade(
        user_id=user.id,
        symbol=ticker,
        quantity=qty,
        price=market_price,
        trade_type="BUY",
        trade_mode=strategy,
        leverage=leverage,
        stop_loss=stop_loss_value,
        target_price=None,
        status="OPEN"
    )

    new_trade.calculate_total()

    db.session.add(new_trade)
    db.session.commit()

    return {
        "status": "AI Trade Executed",
        "symbol": ticker,
        "mode": strategy,
        "quantity": qty
    }, 200