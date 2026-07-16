#!/usr/bin/env python3
"""
Daily price checker for a personal list of Coles & Woolworths items.

Reads items.json, fetches the current price for each item's Coles and/or
Woolworths URL, and appends a timestamped snapshot to history.json.

This is designed for personal use on a small list (~25 items), checked
about once a day. Please keep it that way -- don't crank up the frequency
or the item count a lot. Low-volume, infrequent checks are the difference
between "one person keeping an eye on their shopping list" and "load on
someone else's servers", and the latter is what gets scrapers blocked.

Neither Coles' nor Woolworths' JSON structure is officially documented,
so this may need small tweaks over time if they change their site.
Errors are printed clearly per item so you can see what broke.
"""

import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-AU,en;q=0.9",
}

ITEMS_FILE = Path("items.json")
HISTORY_FILE = Path("history.json")
REQUEST_DELAY_SECONDS = 3  # be polite - don't hammer either site


def find_price_dict(obj, depth=0):
    """Recursively search a parsed JSON blob for something that looks like
    a Coles-style pricing object: {"now": 3.5, "was": 4.0, "comparable": ...}
    """
    if depth > 12:
        return None
    if isinstance(obj, dict):
        keys_lower = {k.lower() for k in obj.keys()}
        if "now" in keys_lower and any(k in keys_lower for k in ("was", "comparable")):
            return obj
        for v in obj.values():
            found = find_price_dict(v, depth + 1)
            if found:
                return found
    elif isinstance(obj, list):
        for entry in obj:
            found = find_price_dict(entry, depth + 1)
            if found:
                return found
    return None


def scrape_coles(url):
    resp = requests.get(url, headers=HEADERS, timeout=20)
    resp.raise_for_status()

    match = re.search(
        r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', resp.text, re.DOTALL
    )
    if not match:
        raise ValueError(
            "No __NEXT_DATA__ block found on the Coles page — "
            "the site layout may have changed."
        )

    data = json.loads(match.group(1))
    pricing = find_price_dict(data)
    if not pricing:
        # Lowercase key variant, just in case
        pricing = find_price_dict(json.loads(json.dumps(data).lower()))
    if not pricing:
        raise ValueError(
            "Page loaded but no pricing block was found inside it — "
            "the JSON structure may have changed."
        )

    def num(key):
        v = pricing.get(key)
        return float(v) if v is not None else None

    return {
        "price": num("now"),
        "was_price": num("was"),
        "unit_price": num("comparable"),
    }


def extract_stockcode(url):
    match = re.search(r"/productdetails/(\d+)", url) or re.search(r"/product/(\d+)", url)
    if not match:
        raise ValueError(f"Couldn't find a Woolworths stockcode in URL: {url}")
    return match.group(1)


def scrape_woolworths(url):
    stockcode = extract_stockcode(url)

    # Try the direct product API first (fast path)
    api_url = f"https://www.woolworths.com.au/apis/ui/product/detail/{stockcode}"
    try:
        resp = requests.get(api_url, headers=HEADERS, timeout=20)
        if resp.ok:
            data = resp.json()
            product = data[0] if isinstance(data, list) and data else data
            if isinstance(product, dict) and product.get("Price") is not None:
                return {
                    "price": product.get("Price"),
                    "was_price": product.get("WasPrice") or product.get("InstoreWasPrice"),
                    "unit_price": product.get("CupPrice"),
                }
    except (requests.RequestException, ValueError, KeyError, IndexError):
        pass  # fall through to the HTML fallback below

    # Fallback: the same JSON is embedded in the regular product page HTML
    resp = requests.get(url, headers=HEADERS, timeout=20)
    resp.raise_for_status()

    price_match = re.search(r'"Price"\s*:\s*([\d.]+)', resp.text)
    was_match = re.search(r'"WasPrice"\s*:\s*([\d.]+)', resp.text)
    if not price_match:
        raise ValueError(
            "Couldn't find a price on the Woolworths page — "
            "the site layout may have changed, or the page didn't load fully."
        )

    return {
        "price": float(price_match.group(1)),
        "was_price": float(was_match.group(1)) if was_match else None,
        "unit_price": None,
    }


def main():
    if not ITEMS_FILE.exists():
        print("items.json not found.", file=sys.stderr)
        sys.exit(1)

    items = json.loads(ITEMS_FILE.read_text())
    history = json.loads(HISTORY_FILE.read_text()) if HISTORY_FILE.exists() else {}

    timestamp = datetime.now(timezone.utc).isoformat()
    had_errors = False

    for item in items:
        item_id = item["id"]
        history.setdefault(item_id, {"name": item["name"], "snapshots": []})
        history[item_id]["name"] = item["name"]  # keep name in sync if edited

        for store, url_key, scraper in (
            ("coles", "coles_url", scrape_coles),
            ("woolworths", "woolworths_url", scrape_woolworths),
        ):
            url = item.get(url_key)
            if not url:
                continue
            try:
                result = scraper(url)
                history[item_id]["snapshots"].append(
                    {"timestamp": timestamp, "store": store, **result}
                )
                print(f"OK   {item['name']} ({store}): ${result['price']}")
            except Exception as e:
                had_errors = True
                print(f"FAIL {item['name']} ({store}): {e}", file=sys.stderr)

            time.sleep(REQUEST_DELAY_SECONDS)

    HISTORY_FILE.write_text(json.dumps(history, indent=2))

    if had_errors:
        sys.exit(1)  # non-zero exit so the Actions run is flagged red and you notice


if __name__ == "__main__":
    main()
