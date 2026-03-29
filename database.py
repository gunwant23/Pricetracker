"""
database.py — Auto-initialises on import. No manual setup needed.
"""
import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tracker.db")


def _conn():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c


def _init():
    with _conn() as c:
        c.executescript("""
            CREATE TABLE IF NOT EXISTS products (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                url          TEXT UNIQUE NOT NULL,
                title        TEXT,
                target_price REAL NOT NULL,
                added_on     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_checked TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS price_history (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER NOT NULL,
                price      REAL    NOT NULL,
                checked_on TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS config (
                key   TEXT PRIMARY KEY,
                value TEXT
            );
        """)


# ── Products ──────────────────────────────────────────────────────────────────

def add_product(url, title, current_price, target_price):
    with _conn() as c:
        cur = c.execute(
            "INSERT OR IGNORE INTO products (url, title, target_price) VALUES (?,?,?)",
            (url, title, target_price),
        )
        pid = cur.lastrowid or c.execute("SELECT id FROM products WHERE url=?", (url,)).fetchone()["id"]
        c.execute("INSERT INTO price_history (product_id, price) VALUES (?,?)", (pid, current_price))
    return pid


def get_all_products():
    with _conn() as c:
        return c.execute("SELECT * FROM products ORDER BY added_on ASC").fetchall()


def url_exists(url):
    with _conn() as c:
        return c.execute("SELECT 1 FROM products WHERE url=?", (url,)).fetchone() is not None


def delete_product(pid):
    with _conn() as c:
        c.execute("DELETE FROM price_history WHERE product_id=?", (pid,))
        c.execute("DELETE FROM products WHERE id=?", (pid,))


def update_target(pid, target):
    with _conn() as c:
        c.execute("UPDATE products SET target_price=? WHERE id=?", (target, pid))


def update_title(pid, title):
    with _conn() as c:
        c.execute("UPDATE products SET title=? WHERE id=?", (title, pid))


def set_last_checked(pid):
    with _conn() as c:
        c.execute("UPDATE products SET last_checked=? WHERE id=?",
                  (datetime.now().strftime("%Y-%m-%d %H:%M"), pid))


def get_last_checked_all():
    with _conn() as c:
        rows = c.execute("SELECT id, last_checked FROM products").fetchall()
    return {r["id"]: r["last_checked"] for r in rows}


# ── Price history ─────────────────────────────────────────────────────────────

def log_price(pid, price):
    with _conn() as c:
        c.execute("INSERT INTO price_history (product_id, price) VALUES (?,?)", (pid, price))


def get_history(pid):
    with _conn() as c:
        return c.execute(
            "SELECT price, checked_on FROM price_history WHERE product_id=? ORDER BY checked_on ASC",
            (pid,),
        ).fetchall()


def get_lowest_price(pid):
    with _conn() as c:
        row = c.execute("SELECT MIN(price) FROM price_history WHERE product_id=?", (pid,)).fetchone()
        return row[0] if row else None


# ── Email config ──────────────────────────────────────────────────────────────

def save_email_config(to_email, smtp_user, smtp_pass):
    with _conn() as c:
        for k, v in [("to_email", to_email), ("smtp_user", smtp_user), ("smtp_pass", smtp_pass)]:
            c.execute("INSERT OR REPLACE INTO config (key, value) VALUES (?,?)", (k, v))


def get_email_config():
    with _conn() as c:
        rows = c.execute("SELECT key, value FROM config").fetchall()
    return {r["key"]: r["value"] for r in rows}


_init()
