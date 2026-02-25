from flask import Blueprint, render_template, request
from flask_login import login_required, current_user
import yfinance as yf
import plotly.graph_objs as go

dashboard = Blueprint("dashboard", __name__)

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

# 5 IMPORTANT STOCKS (Always Highlighted)
PRIORITY_STOCKS = [
"SBIN.NS","IRCTC.NS",
"TATAMOTORS.NS","BEL.NS","INDIGO.NS"
]

# ---------------- DASHBOARD ----------------

@dashboard.route("/dashboard")
@login_required
def dashboard_page():

    stocks = []

    try:
        # ✅ SINGLE BULK REQUEST
        data = yf.download(
            tickers=" ".join(TOP_100_STOCKS),
            period="1d",
            interval="1d",
            group_by="ticker",
            threads=False
        )

        for symbol in TOP_100_STOCKS:
            try:
                if symbol not in data:
                    continue

                stock_df = data[symbol]

                if stock_df.empty:
                    continue

                price = round(float(stock_df["Close"].dropna().iloc[-1]), 2)

                stocks.append({
                    "symbol": symbol,
                    "price": price,
                    "priority": symbol in PRIORITY_STOCKS
                })

            except:
                continue

    except Exception as e:
        print("Dashboard Error:", e)

    return render_template(
        "dashboard.html",
        stocks=stocks,
        balance=current_user.balance
    )


# ---------------- STOCK DETAIL ----------------

@dashboard.route("/stock/<symbol>")
@login_required
def stock_detail(symbol):

    period = request.args.get("period", "1d")

    interval_map = {
        "1d": "5m",
        "7d": "15m",
        "1mo": "1h",
        "6mo": "1d",
        "1y": "1d",
        "5y": "1wk"
    }

    interval = interval_map.get(period, "1d")

    try:
        data = yf.download(symbol, period=period, interval=interval)

        # Fallback to daily if intraday fails
        if data.empty:
            data = yf.download(symbol, period="1mo", interval="1d")

        if data.empty:
            return render_template(
                "stock_detail.html",
                symbol=symbol,
                chart="<h4>Market data unavailable</h4>",
                price=None
            )

        current_price = round(float(data["Close"].iloc[-1]), 2)

        fig = go.Figure()

        fig.add_trace(go.Candlestick(
            x=data.index,
            open=data['Open'],
            high=data['High'],
            low=data['Low'],
            close=data['Close'],
            increasing_line_color='green',
            decreasing_line_color='red'
        ))

        fig.update_layout(
            template="plotly_dark",
            height=550,
            xaxis_rangeslider_visible=False,
            margin=dict(l=20, r=20, t=30, b=20)
        )

        chart = fig.to_html(full_html=False)

    except Exception as e:
        print("Stock Detail Error:", e)
        chart = "<h4>Error loading chart</h4>"
        current_price = None

    return render_template(
        "stock_detail.html",
        symbol=symbol,
        chart=chart,
        price=current_price
    )