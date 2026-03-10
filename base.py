import streamlit as st
import sqlite3
import random
import os
import time
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

# -------- MARKET -------- #

if "dc_price" not in st.session_state:
    st.session_state.dc_price = 1.0

def update_market():
    change = random.uniform(-0.05,0.05)
    st.session_state.dc_price += change

    if st.session_state.dc_price < 0.1:
        st.session_state.dc_price = 0.1

# -------- FUNCTIONS -------- #

def create_user(username):
    c.execute("""
    INSERT INTO users(username, balance, dc)
    VALUES(?,0,0)
    """,(username,))
    conn.commit()

def get_user(username):
    c.execute("SELECT * FROM users WHERE username=?", (username,))
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
        c.execute("""
        UPDATE earnings SET amount = amount + ?
        WHERE username=? AND date=?
        """, (amount, username, today))
    else:
        c.execute("""
        INSERT INTO earnings(username, date, amount)
        VALUES(?, ?, ?)
        """, (username, today, amount))

    conn.commit()


def get_weekly_data(username):

    days = ["Sun","Mon","Tue","Wed","Thu","Fri","Sat"]
    values = [0]*7

    c.execute("SELECT date, amount FROM earnings WHERE username=?", (username,))
    rows = c.fetchall()

    for date_str, amount in rows:
        d = datetime.fromisoformat(date_str)
        idx = (d.weekday() + 1) % 7
        values[idx] += amount

    return days, values

# -------- SESSION -------- #

if "user" not in st.session_state:
    st.session_state.user = None

if "page" not in st.session_state:
    st.session_state.page = "home"

if "show_result" not in st.session_state:
    st.session_state.show_result = False

if "cooldown_until" not in st.session_state:
    st.session_state.cooldown_until = None

# -------- LOGIN -------- #

if not st.session_state.user:

    st.title("🪙 Duckbase")

    username = st.text_input("Set Username")

    if st.button("Start"):
        if username:
            if not get_user(username):
                create_user(username)

            st.session_state.user = username
            st.rerun()

# -------- MAIN APP -------- #

else:

    user = get_user(st.session_state.user)

    if not user:
        st.session_state.user = None
        st.rerun()

    username = user[0]
    balance = user[1]
    dc = user[2]

    with st.sidebar:

        st.markdown("## 🪙 Duckbase")
        st.image("Screenshot 2026-03-04 103323.png")
        st.write(username)

        if st.button("Home"):
            st.session_state.page = "home"

        if st.button("Earn DC"):
            st.session_state.page = "earn"

        if st.button("Trading"):
            st.session_state.page = "trade"

        if st.button("Live Market"):
            st.session_state.page = "market"

    # -------- HOME -------- #

    if st.session_state.page == "home":

        st.markdown(f"# 🪙 {balance} DC")

        st.html('<h1 style="font-size:40px;"><b>DuckPlot</b></h1>')

        fig, ax = plt.subplots()
        fig.patch.set_facecolor("#0e1117")
        ax.set_facecolor("#0e1117")

        c.execute("SELECT username FROM users")
        all_users = [u[0] for u in c.fetchall()]

        for u in all_users:

            days, values = get_weekly_data(u)

            ax.plot(days, values, linewidth=2, label=u)

        ax.tick_params(colors='white')

        for spine in ax.spines.values():
            spine.set_color("white")

        ax.legend(facecolor="#0e1117", edgecolor="white", labelcolor="white")

        st.pyplot(fig)

        st.header("What's Duckbase Coin (DC)?")

        st.markdown("""
Duckbase Coin (DC) is the main currency of Duckbase.

You can:

• Earn DC  
• Trade DC  
• Watch the live market  

The market is controlled by the built-in trading bot **DuckAI**.
""")

    # -------- EARN -------- #

    if st.session_state.page == "earn":

        st.header("Earn Duckbase Coin (DC)")

        st.markdown("""
Select number between 0 to 9 and click Start.  
If matched, you earn **1 DC**.
""")

        selected_number = st.selectbox("Pick a number", list(range(10)))

        now = datetime.now()

        if st.session_state.cooldown_until:

            remaining = (st.session_state.cooldown_until - now).total_seconds()

            if remaining > 0:
                st.warning(f"⏳ Wait {int(remaining)} seconds before next try.")
                st.stop()
            else:
                st.session_state.cooldown_until = None

        if st.button("Start"):

            result = random.randint(0, 9)

            st.session_state.last_result = result
            st.session_state.selected_number = selected_number
            st.session_state.show_result = True

            st.session_state.cooldown_until = datetime.now() + timedelta(minutes=1)

        if st.session_state.show_result:

            st.markdown(f"Result: {st.session_state.last_result}")

            if st.session_state.selected_number == st.session_state.last_result:

                update_balance(username, 1)

                st.balloons()
                st.success("You won 1 DC!")
                st.rerun()

            else:
                st.error("You lost!")

            time.sleep(3)

            st.session_state.show_result = False
            st.rerun()

    # -------- TRADING -------- #

    if st.session_state.page == "trade":

        st.header("Duckbase Exchange")

        update_market()

        price = st.session_state.dc_price

        st.subheader(f"Current DC Price: ${round(price,3)}")

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
                st.error("Not enough DC balance")

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
                st.error("You don't have enough DC")

    # -------- LIVE CANDLE MARKET -------- #

    if st.session_state.page == "market":

        st.header("Live Duckbase Market")

        prices=[]
        base=st.session_state.dc_price

        for i in range(30):

            open_p=base+random.uniform(-0.05,0.05)
            close_p=open_p+random.uniform(-0.05,0.05)
            high=max(open_p,close_p)+random.uniform(0,0.05)
            low=min(open_p,close_p)-random.uniform(0,0.05)

            prices.append([open_p,high,low,close_p])
            base=close_p

        fig,ax=plt.subplots()

        for i,p in enumerate(prices):

            o,h,l,c=p
            color="green" if c>o else "red"

            ax.plot([i,i],[l,h],color=color)
            ax.plot([i,i],[o,c],linewidth=6,color=color)

        fig.patch.set_facecolor("#0e1117")
        ax.set_facecolor("#0e1117")
        ax.tick_params(colors='white')

        st.pyplot(fig)

with st.sidebar:
    st.link_button("Discord","https://discord.gg/Wdkq2Fy2")
