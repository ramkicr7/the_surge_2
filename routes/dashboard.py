from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from models import Trade
from extensions import db
import yfinance as yf
import plotly.graph_objs as go
import pandas as pd
import datetime
dashboard = Blueprint("dashboard", __name__)
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

        # -------- PERFORMANCE --------
        performance = {
            "open": info.get("open"),
            "prev_close": info.get("previousClose"),
            "day_low": info.get("dayLow"),
            "day_high": info.get("dayHigh"),
            "52w_low": info.get("fiftyTwoWeekLow"),
            "52w_high": info.get("fiftyTwoWeekHigh"),
            "volume": info.get("volume")
        }

        # -------- FUNDAMENTALS --------
        fundamentals = {
            "market_cap": info.get("marketCap"),
            "pe_ratio": info.get("trailingPE"),
            "eps": info.get("trailingEps"),
            "book_value": info.get("bookValue"),
            "roe": info.get("returnOnEquity"),
            "debt_to_equity": info.get("debtToEquity"),
            "dividend_yield": info.get("dividendYield")
        }

        # -------- CHART DATA --------
        if period == "1d":
            data = ticker.history(period="5d", interval="5m")
            if not data.empty:
                data = data[data.index.date == data.index[-1].date()]

        elif period == "7d":
            data = ticker.history(period="1mo", interval="15m")
            if not data.empty:
                last_7 = data.index[-1] - pd.Timedelta(days=7)
                data = data[data.index >= last_7]

        elif period == "1mo":
            data = ticker.history(period="1mo", interval="1h")

        elif period == "6mo":
            data = ticker.history(period="6mo", interval="1d")

        elif period == "1y":
            data = ticker.history(period="1y", interval="1d")

        elif period == "5y":
            data = ticker.history(period="5y", interval="1wk")

        else:
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

        x_axis = data["Datetime"] if "Datetime" in data.columns else data["Date"]

        fig.add_trace(go.Candlestick(
            x=x_axis,
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
import datetime

@dashboard.route("/portfolio")
@login_required
def portfolio():

    trades = Trade.query.filter(
        Trade.user_id == current_user.id,
        Trade.status == "OPEN"
    ).all()

    portfolio_data = {}

    for trade in trades:

        key = (trade.symbol, trade.trade_mode)

        if key not in portfolio_data:
            portfolio_data[key] = {
                "symbol": trade.symbol,
                "trade_mode": trade.trade_mode,
                "quantity": 0,
                "total_cost": 0,
                "stop_loss": trade.stop_loss,
                "target_price": trade.target_price,
                "timestamp": trade.timestamp
            }

        if trade.trade_type == "BUY":
            portfolio_data[key]["quantity"] += trade.quantity
            portfolio_data[key]["total_cost"] += trade.price * trade.quantity

        elif trade.trade_type == "SELL":
            portfolio_data[key]["quantity"] -= trade.quantity
            portfolio_data[key]["total_cost"] -= trade.price * trade.quantity


    holdings = []
    intraday_positions = []

    for (symbol, mode), data in portfolio_data.items():

        if data["quantity"] <= 0:
            continue

        avg_price = data["total_cost"] / data["quantity"]

        holding_days = 0
        if mode == "SWING":
            holding_days = (
                datetime.datetime.utcnow() - data["timestamp"]
            ).days

        record = {
            "symbol": symbol,
            "quantity": data["quantity"],
            "avg_price": round(avg_price, 2),
            "trade_mode": mode,
            "holding_days": holding_days,
            "stop_loss": data["stop_loss"],
            "target_price": data["target_price"]
        }

        # 🔥 Separate Intraday
        if mode == "INTRADAY":
            intraday_positions.append(record)
        else:
            holdings.append(record)

    return render_template(
        "portfolio.html",
        holdings=holdings,
        intraday_positions=intraday_positions
    )