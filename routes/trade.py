from flask import Blueprint, redirect, flash
from flask_login import login_required, current_user
from models import Trade
from extensions import db
import yfinance as yf

trade = Blueprint("trade", __name__)

# ---------------- SAFE PRICE FETCH FUNCTION ----------------

def get_live_price(symbol):
    try:
        data = yf.Ticker(symbol).history(period="1d")

        if data.empty:
            return None

        return float(data["Close"].iloc[-1])

    except:
        return None


# ---------------- BUY ----------------

@trade.route("/buy/<symbol>")
@login_required
def buy(symbol):

    price = get_live_price(symbol)

    if price is None:
        flash("Market data unavailable. Try again.", "danger")
        return redirect("/dashboard")

    quantity = 1
    total_cost = price * quantity

    if current_user.balance >= total_cost:

        current_user.balance -= total_cost

        new_trade = Trade(
            user_id=current_user.id,
            symbol=symbol,
            quantity=quantity,
            price=price,
            trade_type="BUY"
        )

        db.session.add(new_trade)
        db.session.commit()

        flash(f"{symbol} bought at ₹{round(price,2)}", "success")

    else:
        flash("Insufficient balance", "danger")

    return redirect("/dashboard")


# ---------------- SELL ----------------

@trade.route("/sell/<symbol>")
@login_required
def sell(symbol):

    price = get_live_price(symbol)

    if price is None:
        flash("Market data unavailable. Try again.", "danger")
        return redirect("/dashboard")

    # Check if user owns stock
    buys = Trade.query.filter_by(
        user_id=current_user.id,
        symbol=symbol,
        trade_type="BUY"
    ).all()

    sells = Trade.query.filter_by(
        user_id=current_user.id,
        symbol=symbol,
        trade_type="SELL"
    ).all()

    total_bought = sum(t.quantity for t in buys)
    total_sold = sum(t.quantity for t in sells)

    holdings = total_bought - total_sold

    if holdings <= 0:
        flash("No holdings to sell.", "danger")
        return redirect("/dashboard")

    quantity = 1

    current_user.balance += price * quantity

    new_trade = Trade(
        user_id=current_user.id,
        symbol=symbol,
        quantity=quantity,
        price=price,
        trade_type="SELL"
    )

    db.session.add(new_trade)
    db.session.commit()

    flash(f"{symbol} sold at ₹{round(price,2)}", "success")

    return redirect("/dashboard")