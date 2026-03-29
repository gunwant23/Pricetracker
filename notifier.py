"""
notifier.py — Email alert when price hits target.
"""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


def alert(product_title, current_price, target_price, url,
          to_email="", smtp_user="b230611@skit.ac.in", smtp_pass="lqoi pfjd sntq xsiz"):

    # Desktop popup (if plyer installed)
    try:
        import plyer
        plyer.notification.notify(
            title="🔔 Price Drop!",
            message=f"{product_title[:50]}\n₹{current_price:,.0f} — target reached!",
            timeout=10,
        )
    except Exception:
        pass

    if not (to_email and smtp_user and smtp_pass):
        return

    subject = f"🔔 Price Drop Alert: {product_title[:50]}"
    body = f"""Hi,

Great news — the price just dropped to your target!

Product  : {product_title}
Price now: ₹{current_price:,.0f}
Target   : ₹{target_price:,.0f}

👉 Buy now: {url}

— PriceTracker
"""
    msg = MIMEMultipart()
    msg["From"]    = smtp_user
    msg["To"]      = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as s:
            s.ehlo(); s.starttls()
            s.login(smtp_user, smtp_pass)
            s.sendmail(smtp_user, to_email, msg.as_string())
    except Exception as e:
        print(f"[Email error] {e}")
