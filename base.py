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

conn = sqlite3.connect("duckbase.db", check_same_thread=False)
c = conn.cursor()

c.execute("""
CREATE TABLE IF NOT EXISTS users(
    username TEXT PRIMARY KEY,
    balance INTEGER DEFAULT 0,
    pfp TEXT,
    duck_card INTEGER DEFAULT 0,
    duck_coin INTEGER DEFAULT 0
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

def create_user(username, pfp):
    os.makedirs("pfps", exist_ok=True)
    pfp_path = f"pfps/{username}.png"

    with open(pfp_path, "wb") as f:
        f.write(pfp.getbuffer())

    c.execute("""
    INSERT INTO users(username, balance, pfp, duck_card, duck_coin)
    VALUES(?, 0, ?, 0, 0)
    """, (username, pfp_path))

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

    # Already purchased
    if item == "ducksilver" and user[4] == 1:
        return "already"

    if item == "duckgold" and user[5] == 1:
        return "already"

    # Not enough balance
    if balance < price:
        return "insufficient"

    # Purchase
    if item == "duck_card":
        c.execute("UPDATE users SET duck_card=1, balance=balance-? WHERE username=?",
                  (price, username))

    if item == "duck_coin":
        c.execute("UPDATE users SET duck_coin=1, balance=balance-? WHERE username=?",
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
    pfp = st.file_uploader("Upload Profile Picture", type=["png","jpg","jpeg"])

    if st.button("Start"):
        if username and pfp:
            if not get_user(username):
                create_user(username, pfp)

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
    pfp_path = user[2]
    duck_card = user[-2]
    duck_coin = user[-1]

    # SIDEBAR
    with st.sidebar:
        st.markdown("## 🪙 Duckbase")
        st.image(pfp_path, width=120)
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

        st.subheader("Base Over Time")

        days, values = get_weekly_data(username)

        fig, ax = plt.subplots()
        fig.patch.set_facecolor("#0e1117")
        ax.set_facecolor("#0e1117")

        ax.plot(days, values)
        ax.set_xlabel("Day", color="white")
        ax.set_ylabel("Base Earned", color="white")

        ax.tick_params(colors='white')

        for spine in ax.spines.values():
            spine.set_color("white")

        st.pyplot(fig)

    # -------- EARN -------- #

    if st.session_state.page == "earn":

        st.header("Earn Base")

        st.markdown("""
Select number between 0 to 9 and click Start.  
If matched, you earn 1 Base 🪙.
""")

        selected_number = st.selectbox("Pick a number",list(range(10)))
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

        if st.button("Buy Duck Coin"):
            result = buy_item(username, "ducksilver", 10)

            if result == "already":
                st.info("Already Purchased")
                

            elif result == "insufficient":
                st.error("Insufficient base!")

            elif result == "success":
                st.success("Duck Card Purchased 🪙")
                time.sleep(1)
                st.rerun()

        st.subheader("Duck Coin (Gold)- 🪙50")

        if st.button("Buy Duck Coin"):
            result = buy_item(username, "duckgold", 50)

            if result == "already":
                st.image("Gemini_Generated_Image_2phh422phh422phh.png")
                st.info("Already Purchased")

            elif result == "insufficient":
                st.error("Insufficient base!")

            elif result == "success":
                st.image("Gemini_Generated_Image_2phh422phh422phh.png")
                st.success("Duck Coin Purchased 🪙")
                time.sleep(1)

                st.rerun()










