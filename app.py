"""
app.py — PriceTracker
Track up to 3 Flipkart products. Auto-checks every 24h. Email when price drops.

Run: streamlit run app.py
"""
import threading
import time
from datetime import datetime

import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

import database as db
from scraper import scrape_price
from notifier import alert

MAX_PRODUCTS = 3

# ─────────────────────────────────────────────────────────────────────────────
# Background auto-checker — runs every 24 h inside a daemon thread
# ─────────────────────────────────────────────────────────────────────────────

def _run_checks():
    """Fetch price for every tracked product and send alerts if target hit."""
    for p in db.get_all_products():
        try:
            data  = scrape_price(p["url"])
            price = data["price"]
            pid   = p["id"]
            db.log_price(pid, price)
            db.set_last_checked(pid)
            if data["title"] != p["title"]:
                db.update_title(pid, data["title"])
            cfg = db.get_email_config()
            if price <= p["target_price"] and cfg.get("to_email"):
                alert(
                    product_title=data["title"],
                    current_price=price,
                    target_price=p["target_price"],
                    url=p["url"],
                    to_email=cfg["to_email"],
                    smtp_user=cfg.get("smtp_user", ""),
                    smtp_pass=cfg.get("smtp_pass", ""),
                )
        except Exception:
            pass   # scrape failures are common — skip silently


def _background_loop():
    while True:
        time.sleep(86400)   # 24 hours
        _run_checks()


def _start_scheduler():
    if not st.session_state.get("_checker_running"):
        t = threading.Thread(target=_background_loop, daemon=True)
        t.start()
        st.session_state["_checker_running"] = True


# ─────────────────────────────────────────────────────────────────────────────
# Page setup
# ─────────────────────────────────────────────────────────────────────────────

st.set_page_config(page_title="PriceTracker 🔔", page_icon="🔔", layout="centered")
_start_scheduler()

st.markdown("""
<style>
[data-testid="stAppViewContainer"] { background: #0f1117; }
.card {
    border-radius: 14px;
    padding: 22px 26px;
    margin-bottom: 18px;
}
.card-deal  { background: #0a2e22; border: 1.5px solid #64ffda; }
.card-wait  { background: #181c2e; border: 1.5px solid #2d3250; }
.lbl  { font-size: 11px; color: #8892b0; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 2px; }
.val  { font-size: 26px; font-weight: 700; color: #e6f1ff; }
.val-green { color: #64ffda; }
.val-yellow { color: #f8c555; }
.prod-title { font-size: 16px; font-weight: 600; color: #e6f1ff; margin-bottom: 14px; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# Sidebar — Email setup + checker status
# ─────────────────────────────────────────────────────────────────────────────

with st.sidebar:
    st.header("📧 Email Setup")
    st.caption("Set once — we'll email you whenever a price hits your target.")

    cfg = db.get_email_config()

    with st.form("email_form"):
        to_email  = st.text_input("Notify me at",       value=cfg.get("to_email",""),  placeholder="you@gmail.com")
        if st.form_submit_button("💾 Save email settings", use_container_width=True):
            db.save_email_config(to_email, smtp_user, smtp_pass)
            st.success("✅ Saved!")

    st.caption("[How to get a Gmail App Password →](https://myaccount.google.com/apppasswords)")

    st.divider()
    st.header("🕐 Auto-check Status")
    st.success("✅ Running — checks every 24 h")

    products = db.get_all_products()
    last_map = db.get_last_checked_all()
    for p in products:
        lc = last_map.get(p["id"], "Not yet")
        name = (p["title"] or "Product")[:28]
        st.caption(f"**{name}**  \nLast checked: {lc}")

# ─────────────────────────────────────────────────────────────────────────────
# Header
# ─────────────────────────────────────────────────────────────────────────────

st.title("🔔 PriceTracker")
st.caption(
    "Paste a Flipkart link · set your target price · we check every 24 h · "
    "email you the moment it drops."
)

products = db.get_all_products()

# ─────────────────────────────────────────────────────────────────────────────
# Add product form
# ─────────────────────────────────────────────────────────────────────────────

slots_used = len(products)
st.subheader(f"Track a product  ({slots_used}/{MAX_PRODUCTS})")

if slots_used >= MAX_PRODUCTS:
    st.warning("You're using all 3 slots. Remove a product below to add a new one.")
else:
    with st.form("add_form", clear_on_submit=True):
        col_url, col_price = st.columns([3, 1])
        with col_url:
            new_url = st.text_input(
                "Flipkart product URL",
                placeholder="https://www.flipkart.com/samsung-galaxy-m34-5g/p/...",
            )
        with col_price:
            new_target = st.number_input("Alert me at ₹", min_value=100, value=15000, step=500)

        add_btn = st.form_submit_button("🔍 Fetch & Start Tracking", use_container_width=True)

    if add_btn:
        if not new_url.strip():
            st.error("Please paste a Flipkart URL.")
        elif "flipkart.com" not in new_url:
            st.error("Only Flipkart URLs are supported.")
        elif db.url_exists(new_url.strip()):
            st.warning("Already tracking this product.")
        else:
            with st.spinner("Fetching current price from Flipkart…"):
                try:
                    data = scrape_price(new_url.strip())
                    db.add_product(
                        url=new_url.strip(),
                        title=data["title"],
                        current_price=data["price"],
                        target_price=float(new_target),
                    )
                    st.success(
                        f"✅ Tracking **{data['title']}**  |  "
                        f"Current price ₹{data['price']:,.0f}  |  "
                        f"Alert target ₹{new_target:,.0f}"
                    )
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ {e}")
                    st.info("Flipkart sometimes blocks scraping. Wait a minute and try again.")

st.divider()

# ─────────────────────────────────────────────────────────────────────────────
# Product cards
# ─────────────────────────────────────────────────────────────────────────────

products = db.get_all_products()

if not products:
    st.info("No products tracked yet. Paste a Flipkart URL above ☝️")
    st.stop()

for p in products:
    pid     = p["id"]
    title   = p["title"] or "Product"
    target  = p["target_price"]
    history = db.get_history(pid)
    low     = db.get_lowest_price(pid)
    current = history[-1]["price"] if history else None
    is_deal = current is not None and current <= target
    card_cls = "card-deal" if is_deal else "card-wait"

    st.markdown(f'<div class="card {card_cls}">', unsafe_allow_html=True)

    # Title row + delete button
    t_col, d_col = st.columns([6, 1])
    with t_col:
        st.markdown(f'<div class="prod-title">{"🟢" if is_deal else "⏳"} {title}</div>',
                    unsafe_allow_html=True)
    with d_col:
        if st.button("✕", key=f"del_{pid}", help="Stop tracking this product"):
            db.delete_product(pid)
            st.rerun()

    # 3 metrics
    m1, m2, m3 = st.columns(3)
    with m1:
        st.markdown('<div class="lbl">Current Price</div>', unsafe_allow_html=True)
        color_cls = "val-green" if is_deal else "val"
        st.markdown(
            f'<div class="val {color_cls}">₹{current:,.0f}</div>' if current else '<div class="val">—</div>',
            unsafe_allow_html=True,
        )
    with m2:
        st.markdown('<div class="lbl">Your Target</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="val">₹{target:,.0f}</div>', unsafe_allow_html=True)
    with m3:
        st.markdown('<div class="lbl">Lowest Ever</div>', unsafe_allow_html=True)
        st.markdown(
            f'<div class="val val-yellow">₹{low:,.0f}</div>' if low else '<div class="val">—</div>',
            unsafe_allow_html=True,
        )

    # Status message
    st.markdown("<br>", unsafe_allow_html=True)
    if is_deal:
        st.success(f"🎉 Price hit your target! **[Buy now on Flipkart →]({p['url']})**")
    elif current and target:
        gap = current - target
        pct = round((current - target) / target * 100, 1)
        st.caption(f"₹{gap:,.0f} ({pct}%) above your target. You'll get an email the moment it drops.")

    # Price graph — shows from day 1 of tracking
    st.markdown("<br>", unsafe_allow_html=True)
    if len(history) >= 2:
        dates  = pd.to_datetime([r["checked_on"] for r in history])
        prices = [r["price"] for r in history]

        fig, ax = plt.subplots(figsize=(7, 2.4))
        fig.patch.set_facecolor("#0f1117")
        ax.set_facecolor("#181c2e")

        ax.plot(dates, prices, color="#64ffda", linewidth=2.2,
                marker="o", markersize=5, zorder=3)
        ax.fill_between(dates, prices, min(prices) * 0.99,
                         alpha=0.12, color="#64ffda")
        ax.axhline(target, color="#ff6b6b", linewidth=1.4,
                   linestyle="--", label=f"Your target  ₹{target:,.0f}", zorder=2)
        if low:
            ax.axhline(low, color="#f8c555", linewidth=1,
                       linestyle=":", label=f"Lowest ever  ₹{low:,.0f}", zorder=2)

        ax.xaxis.set_major_formatter(mdates.DateFormatter("%d %b"))
        fig.autofmt_xdate(rotation=25)
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"₹{x:,.0f}"))
        plt.xticks(color="#8892b0", fontsize=8)
        plt.yticks(color="#8892b0", fontsize=8)
        for sp in ax.spines.values():
            sp.set_edgecolor("#2d3250")
        ax.legend(facecolor="#181c2e", labelcolor="#e6f1ff",
                  fontsize=8, loc="upper right", framealpha=0.9)

        st.pyplot(fig, use_container_width=True)
        plt.close(fig)
    else:
        st.caption("📈 Price graph will appear after the next check. Click **Check now** below to get a second data point.")

    # Actions
    ac1, ac2 = st.columns(2)
    with ac1:
        nt = st.number_input("Change target ₹", value=int(target), step=500, key=f"nt_{pid}")
        if st.button("Update target", key=f"ut_{pid}", use_container_width=True):
            db.update_target(pid, float(nt))
            st.rerun()
    with ac2:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🔄 Check price now", key=f"cn_{pid}", use_container_width=True):
            with st.spinner("Fetching live price…"):
                try:
                    data  = scrape_price(p["url"])
                    price = data["price"]
                    db.log_price(pid, price)
                    db.set_last_checked(pid)
                    cfg2 = db.get_email_config()
                    if price <= target and cfg2.get("to_email"):
                        alert(
                            product_title=data["title"],
                            current_price=price,
                            target_price=target,
                            url=p["url"],
                            to_email=cfg2["to_email"]
                        )
                        st.balloons()
                        st.success("🎉 Target hit! Email sent.")
                    else:
                        st.info(f"Current price: ₹{price:,.0f}")
                    st.rerun()
                except Exception as e:
                    st.error(str(e))

    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("")
