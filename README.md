# 🔔 PriceTracker — Flipkart Price Drop Notifier

Track up to 3 products. Auto-checks every 24h. Emails you when price drops.

## Setup

```bash
pip install -r requirements.txt
streamlit run app.py
```

## How to use

1. **Email setup** — fill the sidebar once with your Gmail + App Password
2. **Add a product** — paste any Flipkart URL, set your target price
3. **That's it** — app checks automatically every 24h while running
4. You get an **email the moment price ≤ target**

## Gmail App Password

1. Enable 2FA on your Google account
2. Visit: https://myaccount.google.com/apppasswords
3. Generate a password → paste it in the sidebar

## Keep it running (so 24h checks happen)

Leave the Streamlit app open in your browser, or run it as a background service.

**Windows — run at startup:**
Add to Task Scheduler:
```
streamlit run C:\path\to\PriceTracker\app.py
```

**Linux/macOS:**
```bash
nohup streamlit run app.py &
```
