import io
import sys
import os
import re
import json
import time
from collections import defaultdict
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

from ticker_resolver import resolve_nse_ticker
from pricing import fetch_stock_prices, init_nifty

MANIFEST_FILE = "video_manifest.json"
EXTRACTIONS_FILE = "all_extracted_stocks.json"
DISCLOSURES_FILE = "host_invested_disclosures.json"
REPORT_OUTPUT = "report.html"

def load_data():
    with open(MANIFEST_FILE, "r", encoding="utf-8") as f:
        manifest = json.load(f)
    with open(EXTRACTIONS_FILE, "r", encoding="utf-8") as f:
        extractions = json.load(f)
    disclosures = {}
    if os.path.exists(DISCLOSURES_FILE):
        with open(DISCLOSURES_FILE, "r", encoding="utf-8") as f:
            disclosures = json.load(f)
    return manifest, extractions, disclosures

def main():
    print("=== Step 1: Loading Extracted Data ===")
    manifest, extractions, disclosures = load_data()
    print(f"Loaded extractions for {len(extractions)} videos.")

    # Flatten records
    flat_records = []
    unique_companies = set()

    IGNORE_ENTITIES = {
        'nifty', 'sensex', 'nifty 50', 'gold', 'n/a', 'quantum liquid fund',
        'bitcoin', 'ethereum', 'crypto', 'bank nifty', 's&p 500', 'nasdaq'
    }

    for vid, data in extractions.items():
        v_date = data.get("date", manifest.get(vid, {}).get("date", "2023-01-01"))
        v_title = data.get("title", manifest.get(vid, {}).get("title", f"Video {vid}"))
        stocks = data.get("stocks", [])

        for s in stocks:
            comp = s.get("company", "").strip()
            if not comp or comp.lower() in IGNORE_ENTITIES:
                continue
            unique_companies.add(comp)
            flat_records.append({
                "video_id": vid,
                "date": v_date,
                "video_title": v_title,
                "company": comp,
                "view": s.get("view", "Neutral"),
                "growth_reasons": s.get("growth_reasons", "No thesis provided."),
                "promoter_details": s.get("promoter_details", "Not explicitly discussed in video"),
                "host_disclosed_holding": s.get("host_disclosed_holding", False),
                "disclosure_quote": s.get("disclosure_quote", "")
            })

    print(f"Total stock recommendations/evaluations extracted: {len(flat_records)}")
    print(f"Unique corporate entities discussed: {len(unique_companies)}")

    print("\n=== Step 2: Resolving Stock Ticker Symbols ===")
    ticker_cache = {}
    for comp in sorted(unique_companies):
        ticker = resolve_nse_ticker(comp)
        ticker_cache[comp] = ticker
        print(f"  {comp:35} -> {ticker if ticker else 'UNLISTED / NOT RESOLVED'}")

    print("\n=== Step 3: Fetching Historical Entry Price & Live Return ===")
    init_nifty()
    pricing_cache_file = "pricing_cache.json"
    pricing_cache = {}
    if os.path.exists(pricing_cache_file):
        try:
            with open(pricing_cache_file, "r", encoding="utf-8") as pf:
                pricing_cache = json.load(pf)
                print(f"Loaded {len(pricing_cache)} cached pricing entries.")
        except Exception:
            pricing_cache = {}

    # Identify needed pricing queries
    needed_queries = set()
    for rec in flat_records:
        comp = rec["company"]
        ticker = ticker_cache.get(comp)
        v_date = rec["date"]
        rec["ticker"] = ticker if ticker else "N/A"
        if ticker and ticker != "N/A":
            cache_key = f"{ticker}::{v_date}"
            if cache_key not in pricing_cache:
                needed_queries.add((ticker, v_date, cache_key))

    print(f"Total unique un-cached price lookups needed: {len(needed_queries)}")

    if needed_queries:
        def fetch_pair(item):
            ticker, v_date, cache_key = item
            p_info = fetch_stock_prices(ticker, v_date)
            return cache_key, p_info

        done_cnt = 0
        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = [executor.submit(fetch_pair, q) for q in needed_queries]
            for future in as_completed(futures):
                cache_key, p_info = future.result()
                done_cnt += 1
                if p_info:
                    pricing_cache[cache_key] = p_info
                if done_cnt % 25 == 0 or done_cnt == len(needed_queries):
                    print(f"  Pricing Progress: {done_cnt}/{len(needed_queries)} queries completed.")
                    with open(pricing_cache_file, "w", encoding="utf-8") as pf:
                        json.dump(pricing_cache, pf, indent=2)

        with open(pricing_cache_file, "w", encoding="utf-8") as pf:
            json.dump(pricing_cache, pf, indent=2)

    # Populate flat records from pricing cache
    for rec in flat_records:
        ticker = rec.get("ticker")
        v_date = rec.get("date")
        if not ticker or ticker == "N/A":
            rec["start_price"] = "N/A"
            rec["current_price"] = "N/A"
            rec["change"] = "N/A"
            rec["nifty_return"] = "N/A"
            rec["nifty_return_pct"] = None
            rec["alpha"] = "N/A"
            rec["alpha_pct"] = None
            continue

        cache_key = f"{ticker}::{v_date}"
        p_info = pricing_cache.get(cache_key)
        if p_info:
            rec["start_price"] = p_info.get("start_price", "N/A")
            rec["current_price"] = p_info.get("current_price", "N/A")
            if p_info.get("change"):
                rec["change"] = p_info["change"]
            else:
                ch = p_info.get("change_pct", "N/A")
                rec["change"] = f"{ch:+.2f}%" if isinstance(ch, (int, float)) else "N/A"
            rec["nifty_return"] = p_info.get("nifty_return", "N/A")
            rec["nifty_return_pct"] = p_info.get("nifty_return_pct")
            rec["alpha"] = p_info.get("alpha", "N/A")
            rec["alpha_pct"] = p_info.get("alpha_pct")
        else:
            rec["start_price"] = "N/A"
            rec["current_price"] = "N/A"
            rec["change"] = "N/A"
            rec["nifty_return"] = "N/A"
            rec["nifty_return_pct"] = None
            rec["alpha"] = "N/A"
            rec["alpha_pct"] = None

    print("\n=== Step 4: Generating Interactive Dashboard (report.html) ===")
    import generate_akshat_html
    generate_akshat_html.generate_html_from_data(flat_records)

    # Save the updated master dataset
    with open("master_stocks_dataset.json", "w", encoding="utf-8") as out:
        json.dump(flat_records, out, indent=2, ensure_ascii=False)

    print(f"\n Master dataset saved to master_stocks_dataset.json")
    print(f" Report successfully built at {REPORT_OUTPUT}")

if __name__ == "__main__":
    main()
