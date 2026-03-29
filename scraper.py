"""
scraper.py — Fetch live price from a Flipkart product URL.
"""
import random, re, time
import requests
from bs4 import BeautifulSoup

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Safari/605.1.15",
]

PRICE_CLASSES = ["Nx9bqj CxhGGd", "aBzdKn", "_30jeq3 _16Jk6d", "_30jeq3", "CEmiEU"]
TITLE_CLASSES = ["VU-ZEz", "B_NuCI", "yhB1nd"]


def _parse_price(text: str):
    digits = re.sub(r"[^\d]", "", text)
    return float(digits) if digits else None


def scrape_price(url: str, retries: int = 3) -> dict:
    """Returns {"title": str, "price": float, "url": str}"""
    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept-Language": "en-IN,en;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Referer": "https://www.flipkart.com/",
    }
    for attempt in range(1, retries + 1):
        try:
            r = requests.get(url, headers=headers, timeout=15)
            r.raise_for_status()
            soup = BeautifulSoup(r.text, "lxml")

            price = None
            for cls in PRICE_CLASSES:
                tag = soup.find(class_=cls)
                if tag:
                    price = _parse_price(tag.get_text())
                    if price:
                        break

            if not price:
                raise ValueError(
                    "Price not found on page. Flipkart may have blocked the request — "
                    "try again in a minute, or open the URL in your browser first."
                )

            title = "Unknown Product"
            for cls in TITLE_CLASSES:
                tag = soup.find(class_=cls)
                if tag:
                    title = tag.get_text(strip=True)
                    break

            return {"title": title, "price": price, "url": url}

        except ValueError:
            raise
        except Exception as e:
            if attempt == retries:
                raise ValueError(f"Network error after {retries} tries: {e}")
            time.sleep(2 ** attempt + random.uniform(0, 1))
