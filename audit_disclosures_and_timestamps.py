import io
import sys
import os
import re
import json

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

EXTRACTIONS_FILE = "all_extracted_stocks.json"
CACHE_DIR = "transcripts_cache"
DISCLOSURES_FILE = "host_invested_disclosures.json"

if not os.path.exists(EXTRACTIONS_FILE):
    print(f"Error: {EXTRACTIONS_FILE} does not exist yet.")
    sys.exit(1)

with open(EXTRACTIONS_FILE, "r", encoding="utf-8") as f:
    extractions = json.load(f)

print(f"Loaded extractions for {len(extractions)} videos.")

disclosures_map = {}
total_disclosures = 0

def format_time(seconds):
    m = int(seconds // 60)
    s = int(seconds % 60)
    return f"{m:02d}:{s:02d}"

for vid, data in extractions.items():
    stocks = data.get("stocks", [])
    title = data.get("title", "")
    date = data.get("date", "")

    seg_file = os.path.join(CACHE_DIR, f"{vid}_segments.json")
    segments = []
    if os.path.exists(seg_file):
        try:
            with open(seg_file, "r", encoding="utf-8") as sf:
                segments = json.load(sf)
        except Exception:
            pass

    for s in stocks:
        is_disclosed = s.get("host_disclosed_holding", False)
        quote = s.get("disclosure_quote", "").strip()
        comp = s.get("company", "").strip()

        if is_disclosed and quote:
            total_disclosures += 1
            print(f"\nFound Disclosure: Video {vid} ({date}) | Stock: {comp}")
            print(f"  Quote: \"{quote}\"")

            # Find exact timestamp using multi-word sliding window across segments
            best_sec = 0
            best_score = 0

            quote_tokens = [w.lower() for w in re.findall(r'\w+', quote) if len(w) > 2]
            comp_tokens = [w.lower() for w in re.findall(r'\w+', comp) if len(w) > 2]

            if segments:
                window_size = 5
                for i in range(len(segments)):
                    window_texts = " ".join([seg.get('text', '').lower() for seg in segments[i:i+window_size]])
                    score = 0
                    for qt in quote_tokens:
                        if qt in window_texts:
                            score += 2
                    for ct in comp_tokens:
                        if ct in window_texts:
                            score += 3

                    if score > best_score:
                        best_score = score
                        best_sec = int(segments[i].get('start', 0))

            time_str = format_time(best_sec)
            yt_link = f"https://youtu.be/{vid}?t={best_sec}s"
            print(f"  Timestamp: {time_str} ({best_sec}s) | Match Score: {best_score} | Link: {yt_link}")

            if vid not in disclosures_map:
                disclosures_map[vid] = []

            disclosures_map[vid].append({
                "video_id": vid,
                "date": date,
                "title": title,
                "company": comp,
                "disclosure_quote": quote,
                "timestamp_sec": best_sec,
                "timestamp_str": time_str,
                "youtube_link": yt_link
            })

with open(DISCLOSURES_FILE, "w", encoding="utf-8") as df:
    json.dump(disclosures_map, df, indent=2, ensure_ascii=False)

print(f"\nAudited all disclosures! Total verified personal disclosures: {total_disclosures}")
print(f"Saved to {DISCLOSURES_FILE}")
