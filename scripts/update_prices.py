"""Fetch latest stock prices from Yahoo Finance and write data/prices.json.

Symbols are collected from data/portfolio.json (main fund) and every
fund's "holdings" in data/site.json. Korean stocks use the .KS suffix.
Run locally with:  python scripts/update_prices.py
"""
import datetime as dt
import json
import pathlib
import sys
import time
import urllib.parse
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
OUT = DATA / "prices.json"
UA = "Mozilla/5.0 (compatible; YIF-price-bot/1.0)"


def collect_symbols():
    syms = []
    port = json.loads((DATA / "portfolio.json").read_text(encoding="utf-8"))
    syms += [h["symbol"] for h in port.get("holdings", [])]
    site = json.loads((DATA / "site.json").read_text(encoding="utf-8"))
    for fund in site.get("funds", []):
        syms += [h["symbol"] for h in fund.get("holdings", [])]
    syms.append("KRW=X")  # USD→KRW exchange rate, used to combine $ and ₩ holdings
    return list(dict.fromkeys(syms))  # de-duplicate, keep order


def iso(ts):
    return dt.datetime.fromtimestamp(ts, dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def fetch(symbol):
    url = ("https://query1.finance.yahoo.com/v8/finance/chart/"
           + urllib.parse.quote(symbol) + "?range=5d&interval=1d")
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=20) as r:
        meta = json.load(r)["chart"]["result"][0]["meta"]
    return {
        "price": meta["regularMarketPrice"],
        "currency": meta.get("currency", "USD"),
        "time": iso(meta.get("regularMarketTime", time.time())),
        "previousClose": meta.get("chartPreviousClose"),
    }


def main():
    old = {}
    if OUT.exists():
        old = json.loads(OUT.read_text(encoding="utf-8")).get("prices", {})
    prices, failed = {}, []
    for sym in collect_symbols():
        try:
            prices[sym] = fetch(sym)
            print(f"ok   {sym:12} {prices[sym]['price']}")
        except Exception as e:  # keep the last known price on failure
            failed.append(sym)
            if sym in old:
                prices[sym] = old[sym]
            print(f"FAIL {sym:12} {e}", file=sys.stderr)
        time.sleep(0.5)
    if failed and len(failed) == len(prices):
        sys.exit("All symbols failed; prices.json left unchanged.")
    out = {"updated": iso(time.time()), "prices": prices}
    OUT.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {OUT.relative_to(ROOT)} ({len(prices)} symbols, {len(failed)} failed)")


if __name__ == "__main__":
    main()
