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
    balance INTEGER DEFAULT 0,
    ducksilver INTEGER DEFAULT 0,
    duckgold INTEGER DEFAULT 0
)
""")

c.execute("""
CREATE TABLE IF NOT EXISTS earnings(
    username TEXT,
    date TEXT,
    amount INTEGER
)
""")

conn.commit()

# -------- FUNCTIONS -------- #

def create_user(username):
    c.execute("""
    INSERT INTO users(username, balance, ducksilver, duckgold)
    VALUES(?, 0, 0, 0)
    """, (username,))
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

def buy_item(username, item, price):
    user = get_user(username)
    balance = user[1]

    if item == "ducksilver" and user[2] == 1:
        return "already"

    if item == "duckgold" and user[3] == 1:
        return "already"

    if balance < price:
        return "insufficient"

    if item == "ducksilver":
        c.execute("UPDATE users SET ducksilver=1, balance=balance-? WHERE username=?",
                  (price, username))

    if item == "duckgold":
        c.execute("UPDATE users SET duckgold=1, balance=balance-? WHERE username=?",
                  (price, username))

    conn.commit()
    return "success"

# -------- SESSION -------- #

if "user" not in st.session_state:
    st.session_state.user = None

if "page" not in st.session_state:
    st.session_state.page = "home"

if "show_result" not in st.session_state:
    st.session_state.show_result = False

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
    duck_card = user[-2]
    duck_coin = user[-1]

    # SIDEBAR
    with st.sidebar:
        st.markdown("## 🪙 Duckbase")
        st.image("Screenshot 2026-03-04 103323.png")
        st.write(username)

        if st.button("Home"):
            st.session_state.page = "home"

        if st.button("Earn Base"):
            st.session_state.page = "earn"

        if st.button("Buy Duck Events"):
            st.session_state.page = "buy"

    # -------- HOME -------- #

    if st.session_state.page == "home":

        st.markdown(f"# 🪙 {balance}")

        st.html('<h1 style="font-size:40px;"><center><b>DuckPlot</b></center></h1>')

        fig, ax = plt.subplots()
        fig.patch.set_facecolor("#0e1117")
        ax.set_facecolor("#0e1117")

        c.execute("SELECT username FROM users")
        all_users = [u[0] for u in c.fetchall()]

        for u in all_users:
            days, values = get_weekly_data(u)

            x = list(range(len(days)))
            smooth_x = []
            smooth_y = []

            for i in range(len(values)-1):
                smooth_x.append(x[i])
                smooth_y.append(values[i])

                mid_x = x[i] + 0.5
                mid_y = (values[i] + values[i+1]) / 2 + random.randint(-3, 3)
                mid_y = max(0, min(50, mid_y))

                smooth_x.append(mid_x)
                smooth_y.append(mid_y)

            smooth_x.append(x[-1])
            smooth_y.append(values[-1])

            total = sum(values)
            color = "#00ff88" if total >= 0 else "#ff4b4b"

            ax.plot(smooth_x, smooth_y, linewidth=2, label=u, color=color)

        ax.set_xticks(range(len(days)))
        ax.set_xticklabels(days)

        ax.set_xlabel("Day", color="white")
        ax.set_ylabel("Base Earned", color="white")

        ax.set_ylim(0, 50)

        ax.tick_params(colors='white')

        for spine in ax.spines.values():
            spine.set_color("white")

        ax.legend(facecolor="#0e1117", edgecolor="white", labelcolor="white")

        st.pyplot(fig)
        st.header("What's DuckBase🪙?")
        st.markdown("__DuckBase__ is a platform in which you can have a __DuckWallet__ where money is called _base_. You can earn _base_ & buy __DuckEvent__. Currently two events are available, more will come soon...🙂")
        st.write("__DuckPlot__ is to see every user's __Base__ data to compare with them.")
    # -------- EARN -------- #

    if st.session_state.page == "earn":

        st.header("Earn Base")

        st.markdown("""
Select number between 0 to 9 and click Start.  
If matched, you earn 1 Base 🪙.
""")

        selected_number = st.selectbox("Pick a number", list(range(10)))

        if st.button("Start"):
            result = random.randint(0, 9)
            st.session_state.last_result = result
            st.session_state.selected_number = selected_number
            st.session_state.show_result = True

        if st.session_state.show_result:

            st.markdown(f"Result: {st.session_state.last_result}")

            if st.session_state.selected_number == st.session_state.last_result:
                update_balance(username, 1)
                st.balloons()
                st.success("You won 1 Base 🪙!")
            else:
                st.error("You lost!")

            time.sleep(3)
            st.session_state.show_result = False
            st.rerun()

    # -------- BUY -------- #

    if st.session_state.page == "buy":

        st.header("Buy Duck Events")

        st.subheader("Duck Coin (Silver) - 🪙10")

        if st.button("Buy Duck Coin", key="buy_silver"):
            result = buy_item(username, "ducksilver", 10)

            if result == "already":
                st.image("Gemini_Generated_Image_xz43glxz43glxz43.png")
                st.info("Already Bought!")

            elif result == "insufficient":
                st.error("Insufficient base!")

            elif result == "success":
                st.image("Gemini_Generated_Image_xz43glxz43glxz43.png")
                st.success("Duck Coin Silver Purchased 🪙")
                time.sleep(1)
                st.rerun()

        st.subheader("Duck Coin (Gold)- 🪙50")

        if st.button("Buy Duck Coin", key="buy_gold"):
            result = buy_item(username, "duckgold", 50)

            if result == "already":
                st.image("Gemini_Generated_Image_2phh422phh422phh.png")
                st.info("Already Bought!")

            elif result == "insufficient":
                st.error("Insufficient base!")

            elif result == "success":
                st.image("Gemini_Generated_Image_2phh422phh422phh.png")
                st.success("Duck Coin Purchased 🪙")
                time.sleep(1)
                st.rerun()
with st.sidebar:
    st.link_button("Discord","https://discord.gg/Wdkq2Fy2")













