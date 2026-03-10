import streamlit as st
import sqlite3
import random
import time
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
import matplotlib.pyplot as plt

st.set_page_config(page_title="Duckbase", page_icon="🪙")

# -------- FORCE DARK MODE -------- #

st.markdown("""
<style>
.stApp {
    background-color: #0e1117;
    color: white;
}
div[data-testid="stSidebar"] {
    background-color: #111827;
}
h1, h2, h3, h4, h5, h6, p, label {
    color: white !important;
}
</style>
""", unsafe_allow_html=True)

# -------- DATABASE -------- #

conn = sqlite3.connect("duckbasex.db", check_same_thread=False)
c = conn.cursor()

c.execute("""
CREATE TABLE IF NOT EXISTS users(
    username TEXT PRIMARY KEY,
    balance REAL DEFAULT 0,
    dc REAL DEFAULT 0
)
""")

c.execute("""
CREATE TABLE IF NOT EXISTS earnings(
    username TEXT,
    date TEXT,
    amount REAL
)
""")

c.execute("""
CREATE TABLE IF NOT EXISTS trades(
    username TEXT,
    type TEXT,
    price REAL,
    amount REAL,
    time TEXT
)
""")

conn.commit()

# -------- MARKET ENGINE -------- #

if "dc_price" not in st.session_state:
    st.session_state.dc_price = 1.0

if "candles" not in st.session_state:
    st.session_state.candles = []

def update_market():

    last = st.session_state.dc_price

    open_p = last
    close_p = open_p + random.uniform(-0.05,0.05)
    high = max(open_p,close_p) + random.uniform(0,0.03)
    low = min(open_p,close_p) - random.uniform(0,0.03)

    st.session_state.dc_price = close_p

    st.session_state.candles.append({
        "time": datetime.now(),
        "open": open_p,
        "high": high,
        "low": low,
        "close": close_p
    })

    if len(st.session_state.candles) > 120:
        st.session_state.candles.pop(0)

# -------- FUNCTIONS -------- #

def create_user(username):
    c.execute("INSERT INTO users VALUES(?,?,?)",(username,0,0))
    conn.commit()

def get_user(username):
    c.execute("SELECT * FROM users WHERE username=?",(username,))
    return c.fetchone()

def update_balance(username, amount):

    c.execute("UPDATE users SET balance = balance + ? WHERE username=?",
              (amount, username))
    conn.commit()

    today = datetime.now().date().isoformat()

    c.execute("SELECT amount FROM earnings WHERE username=? AND date=?",
              (username, today))
    row = c.fetchone()

    if row:
        c.execute("UPDATE earnings SET amount = amount + ? WHERE username=? AND date=?",
                  (amount, username, today))
    else:
        c.execute("INSERT INTO earnings VALUES(?,?,?)",
                  (username, today, amount))

    conn.commit()

def get_weekly_data(username):

    days = ["Sun","Mon","Tue","Wed","Thu","Fri","Sat"]
    values = [0]*7

    c.execute("SELECT date, amount FROM earnings WHERE username=?", (username,))
    rows = c.fetchall()

    for date_str, amount in rows:
        d = datetime.fromisoformat(date_str)
        idx = (d.weekday()+1)%7
        values[idx]+=amount

    return days, values

# -------- SESSION -------- #

if "user" not in st.session_state:
    st.session_state.user=None

if "page" not in st.session_state:
    st.session_state.page="home"

if "show_result" not in st.session_state:
    st.session_state.show_result=False

if "cooldown_until" not in st.session_state:
    st.session_state.cooldown_until=None

# -------- LOGIN -------- #

if not st.session_state.user:

    st.title("🪙 Duckbase")

    username = st.text_input("Set Username")

    if st.button("Start"):
        if username:
            if not get_user(username):
                create_user(username)

            st.session_state.user=username
            st.rerun()

# -------- MAIN APP -------- #

else:

    user=get_user(st.session_state.user)

    username=user[0]
    balance=user[1]
    dc=user[2]

    with st.sidebar:

        st.markdown("## 🪙 Duckbase")
        st.write(username)

        if st.button("Home"):
            st.session_state.page="home"

        if st.button("Earn DC"):
            st.session_state.page="earn"

        if st.button("Trading"):
            st.session_state.page="trade"

    # -------- HOME -------- #

    if st.session_state.page=="home":

        st.markdown(f"# 🪙 {balance} DC")

        st.header("DuckPlot")

        fig, ax = plt.subplots()

        c.execute("SELECT username FROM users")
        all_users=[u[0] for u in c.fetchall()]

        for u in all_users:
            days,values=get_weekly_data(u)
            ax.plot(days,values,label=u)

        ax.legend()
        st.pyplot(fig)

    # -------- EARN -------- #

    if st.session_state.page=="earn":

        st.header("Earn Duckbase Coin (DC)")

        selected_number = st.selectbox("Pick a number", list(range(10)))

        now = datetime.now()

        if st.session_state.cooldown_until:

            remaining = (st.session_state.cooldown_until-now).total_seconds()

            if remaining>0:
                st.warning(f"Wait {int(remaining)} seconds")
                st.stop()
            else:
                st.session_state.cooldown_until=None

        if st.button("Start"):

            result=random.randint(0,9)

            st.session_state.last_result=result
            st.session_state.selected_number=selected_number
            st.session_state.show_result=True

            st.session_state.cooldown_until=datetime.now()+timedelta(minutes=1)

        if st.session_state.show_result:

            st.markdown(f"Result: {st.session_state.last_result}")

            if st.session_state.selected_number==st.session_state.last_result:

                update_balance(username,1)

                st.success("You won 1 DC!")
                st.rerun()

            else:
                st.error("You lost!")

            time.sleep(2)
            st.session_state.show_result=False
            st.rerun()

    # -------- TRADING -------- #

    if st.session_state.page=="trade":

        st.header("Duckbase Exchange")

        update_market()

        price = st.session_state.dc_price

        st.subheader(f"DC Price: ${round(price,3)}")

        # -------- TRADINGVIEW STYLE CANDLE CHART -------- #

        df = pd.DataFrame(st.session_state.candles)

        if len(df) > 2:

            fig = go.Figure(data=[go.Candlestick(
                x=df["time"],
                open=df["open"],
                high=df["high"],
                low=df["low"],
                close=df["close"],
                increasing_line_color='#00ff9f',
                decreasing_line_color='#ff4d4d'
            )])

            fig.update_layout(
                template="plotly_dark",
                height=500,
                xaxis_rangeslider_visible=False,
                paper_bgcolor="#0e1117",
                plot_bgcolor="#0e1117"
            )

            st.plotly_chart(fig, use_container_width=True)

        # -------- BUY SELL -------- #

        amount = st.number_input("Amount",1,100,1)

        if st.button("Buy DC"):

            cost = price * amount

            if balance >= cost:

                c.execute("UPDATE users SET balance=balance-?, dc=dc+? WHERE username=?",
                          (cost, amount, username))
                conn.commit()

                st.success("DuckAI sold DC to you 🪙")

                c.execute("INSERT INTO trades VALUES(?,?,?,?,?)",
                          (username,"BUY",price,amount,str(datetime.now())))
                conn.commit()

                st.rerun()

            else:
                st.error("Not enough balance")

        if st.button("Sell DC"):

            if dc >= amount:

                gain = price * amount

                c.execute("UPDATE users SET balance=balance+?, dc=dc-? WHERE username=?",
                          (gain, amount, username))
                conn.commit()

                st.success("DuckAI bought DC from you 🪙")

                c.execute("INSERT INTO trades VALUES(?,?,?,?,?)",
                          (username,"SELL",price,amount,str(datetime.now())))
                conn.commit()

                st.rerun()

            else:
                st.error("Not enough DC")

with st.sidebar:
    st.link_button("Discord","https://discord.gg/Wdkq2Fy2")
