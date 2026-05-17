from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from models import Trade
from extensions import db
import yfinance as yf
import plotly.graph_objs as go
import pandas as pd
import datetime

dashboard = Blueprint("dashboard", __name__)


# ---------------- UPDATE SWING HOLDING DAYS ----------------

def update_holding_days():

    open_swing_trades = Trade.query.filter_by(
        trade_mode="SWING",
        status="OPEN"
    ).all()

    for trade in open_swing_trades:
        days = (datetime.datetime.utcnow() - trade.timestamp).days
        trade.holding_days = days

    db.session.commit()


# ---------------- SAFE PRICE FETCH ----------------

def get_live_price(symbol):

    try:
        ticker = yf.Ticker(symbol)
        data = ticker.history(period="1d", interval="1m")

        if data.empty:
            return None

        return float(data["Close"].iloc[-1])

    except:
        return None


# ---------------- STOP LOSS CHECK ----------------

def check_stop_loss():

    open_trades = Trade.query.filter_by(status="OPEN").all()

    for trade in open_trades:

        current_price = get_live_price(trade.symbol)

        if not current_price:
            continue

        # STOP LOSS
        if trade.stop_loss and current_price <= trade.stop_loss:
            trade.status = "CLOSED"
            trade.trade_type = "SELL"
            trade.price = current_price

        # TARGET
        if trade.target_price and current_price >= trade.target_price:
            trade.status = "CLOSED"
            trade.trade_type = "SELL"
            trade.price = current_price

    db.session.commit()


# ---------------- STOCK LIST ----------------

TOP_100_STOCKS = [
"SBIN.NS","IRCTC.NS","TATAMOTORS.NS","BEL.NS","INDIGO.NS",
"HDFCBANK.NS","ICICIBANK.NS","AXISBANK.NS","KOTAKBANK.NS",
"BAJFINANCE.NS","RELIANCE.NS","INFY.NS","TCS.NS","HCLTECH.NS",
"WIPRO.NS","LT.NS","ONGC.NS","NTPC.NS","POWERGRID.NS",
"COALINDIA.NS","BPCL.NS","IOC.NS","HINDUNILVR.NS",
"ITC.NS","NESTLEIND.NS","BRITANNIA.NS","TATACONSUM.NS",
"SUNPHARMA.NS","DRREDDY.NS","CIPLA.NS","DIVISLAB.NS",
"MARUTI.NS","M&M.NS","BAJAJ-AUTO.NS","TVSMOTOR.NS",
"EICHERMOT.NS","HEROMOTOCO.NS","TATASTEEL.NS","JSWSTEEL.NS",
"HINDALCO.NS","VEDL.NS","ULTRACEMCO.NS","AMBUJACEM.NS",
"BHARTIARTL.NS","DMART.NS","TRENT.NS","TITAN.NS",
"ZOMATO.NS","PAYTM.NS","IRFC.NS"
]

PRIORITY_STOCKS = [
"SBIN.NS","IRCTC.NS","TATAMOTORS.NS","BEL.NS","INDIGO.NS"
]


# ---------------- DASHBOARD ----------------

@dashboard.route("/dashboard")
@login_required
def dashboard_page():

    stocks = []

    for symbol in TOP_100_STOCKS:

        try:

            ticker = yf.Ticker(symbol)
            data = ticker.history(period="2d", interval="1d")

            if data.empty or len(data) < 2:
                continue

            close_today = float(data["Close"].iloc[-1])
            close_yesterday = float(data["Close"].iloc[-2])
            volume = float(data["Volume"].iloc[-1])

            change_percent = round(
                ((close_today - close_yesterday) / close_yesterday) * 100,
                2
            )

            stocks.append({
                "symbol": symbol,
                "price": round(close_today, 2),
                "change": change_percent,
                "volume": volume,
                "priority": symbol in PRIORITY_STOCKS
            })

        except Exception as e:
            print("Stock fetch error:", symbol, e)
            continue

    most_traded = sorted(stocks, key=lambda x: x["volume"], reverse=True)[:6]
    top_gainers = sorted(stocks, key=lambda x: x["change"], reverse=True)[:6]
    top_losers = sorted(stocks, key=lambda x: x["change"])[:6]

    return render_template(
        "dashboard.html",
        stocks=stocks,
        most_traded=most_traded,
        top_gainers=top_gainers,
        top_losers=top_losers,
        balance=current_user.balance
    )


# ---------------- LIVE PRICE API ----------------

@dashboard.route("/live-price/<symbol>")
@login_required
def live_price(symbol):

    try:

        ticker = yf.Ticker(symbol)
        price = ticker.fast_info.get("last_price")

        if not price:

            data = ticker.history(period="1d", interval="1m")

            if not data.empty:
                price = float(data["Close"].iloc[-1])
            else:
                return jsonify({"error": "No data"})

        return jsonify({
            "symbol": symbol,
            "price": round(float(price), 2)
        })

    except Exception as e:
        print("Live price error:", e)
        return jsonify({"error": "Failed"})


# ---------------- STOCK DETAIL ----------------

@dashboard.route("/stock/<symbol>")
@login_required
def stock_detail(symbol):

    period = request.args.get("period", "1y")

    try:

        ticker = yf.Ticker(symbol)
        info = ticker.info

        performance = {
            "open": info.get("open"),
            "prev_close": info.get("previousClose"),
            "day_low": info.get("dayLow"),
            "day_high": info.get("dayHigh"),
            "52w_low": info.get("fiftyTwoWeekLow"),
            "52w_high": info.get("fiftyTwoWeekHigh"),
            "volume": info.get("volume")
        }

        fundamentals = {
            "market_cap": info.get("marketCap"),
            "pe_ratio": info.get("trailingPE"),
            "eps": info.get("trailingEps"),
            "book_value": info.get("bookValue"),
            "roe": info.get("returnOnEquity"),
            "debt_to_equity": info.get("debtToEquity"),
            "dividend_yield": info.get("dividendYield")
        }

        data = ticker.history(period="1y", interval="1d")

        if data.empty:
            return render_template(
                "stock_detail.html",
                symbol=symbol,
                chart="<h4>No market data available</h4>",
                price=None,
                performance=performance,
                fundamentals=fundamentals
            )

        data.reset_index(inplace=True)

        current_price = round(float(data["Close"].iloc[-1]), 2)

        fig = go.Figure()

        fig.add_trace(go.Candlestick(
            x=data["Date"],
            open=data["Open"],
            high=data["High"],
            low=data["Low"],
            close=data["Close"],
            increasing_line_color="green",
            decreasing_line_color="red"
        ))

        fig.update_layout(
            template="plotly_dark",
            height=600,
            xaxis_rangeslider_visible=False,
            title=f"{symbol} Price Chart"
        )

        chart = fig.to_html(full_html=False)

    except Exception as e:

        print("Stock Detail Error:", e)

        chart = "<h4>Error loading chart</h4>"
        current_price = None
        performance = {}
        fundamentals = {}

    return render_template(
        "stock_detail.html",
        symbol=symbol,
        chart=chart,
        price=current_price,
        performance=performance,
        fundamentals=fundamentals
    )


# ---------------- PORTFOLIO ----------------

@dashboard.route("/portfolio")
@login_required
def portfolio():

    trades = Trade.query.filter(
        Trade.user_id == current_user.id,
        Trade.status == "OPEN"
    ).all()

    holdings = []
    intraday_positions = []

    for trade in trades:

        record = {
            "symbol": trade.symbol,
            "quantity": trade.quantity,
            "avg_price": trade.price,
            "trade_mode": trade.trade_mode,
            "holding_days": 0,
            "stop_loss": trade.stop_loss,
            "target_price": trade.target_price
        }

        if trade.trade_mode == "INTRADAY":
            intraday_positions.append(record)
        else:
            holdings.append(record)

    return render_template(
        "portfolio.html",
        holdings=holdings,
        intraday_positions=intraday_positions
    )


# ---------------- POSITIONS ----------------

@dashboard.route("/positions")
@login_required
def positions():

    trades = Trade.query.filter(
        Trade.user_id == current_user.id,
        Trade.trade_mode == "INTRADAY",
        Trade.status == "OPEN"
    ).all()

    positions_data = {}

    for trade in trades:

        if trade.symbol not in positions_data:

            positions_data[trade.symbol] = {
                "symbol": trade.symbol,
                "buy_qty": 0,
                "sell_qty": 0,
                "buy_value": 0,
                "sell_value": 0
            }

        if trade.trade_type == "BUY":
            positions_data[trade.symbol]["buy_qty"] += trade.quantity
            positions_data[trade.symbol]["buy_value"] += trade.price * trade.quantity

        elif trade.trade_type == "SELL":
            positions_data[trade.symbol]["sell_qty"] += trade.quantity
            positions_data[trade.symbol]["sell_value"] += trade.price * trade.quantity

    final_positions = []

    for symbol, data in positions_data.items():

        net_qty = data["buy_qty"] - data["sell_qty"]

        avg_price = 0

        if data["buy_qty"] > 0:
            avg_price = data["buy_value"] / data["buy_qty"]

        final_positions.append({
            "symbol": symbol,
            "buy_qty": data["buy_qty"],
            "sell_qty": data["sell_qty"],
            "net_qty": net_qty,
            "avg_price": round(avg_price, 2)
        })

    return render_template(
        "positions.html",
        positions=final_positions
    )