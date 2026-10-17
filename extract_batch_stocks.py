import io
import sys
import os
import re
import json
import time
from dotenv import load_dotenv
from google import genai
from google.genai import types

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

load_dotenv()

MANIFEST_FILE = "video_manifest.json"
CACHE_DIR = "transcripts_cache"
OUTPUT_FILE = "all_extracted_stocks.json"

client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

with open(MANIFEST_FILE, "r", encoding="utf-8") as f:
    manifest = json.load(f)

# Priority stock keyword pattern
kw = re.compile(r'stock|share|invest|portfolio|buy|bought|multibagger|dividend|nifty|market|crore|wealth|monopoly|pe|small cap|mid cap|large cap|valuation|tata|reliance|itc|hdfc|bajaj|cams|cdsl|zomato|nykaa|paytm|crash|correction|rally|growth|fund|etf|sector|recession|money', re.I)

# Target videos from 2021 to 2026, prioritizing stock/investing titles first, then date descending
all_vids = list(manifest.values())
all_vids.sort(key=lambda x: (1 if kw.search(x.get('title', '')) else 0, x.get('date', '')), reverse=True)

# Load existing extractions
extractions = {}
if os.path.exists(OUTPUT_FILE):
    try:
        with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
            extractions = json.load(f)
    except Exception:
        extractions = {}

SYSTEM_INSTRUCTION = """You are an elite institutional financial analyst and bilingual NLP extraction engine.
Analyze the provided YouTube video transcripts from Indian finance educator and macro investor Akshat Shrivastava (in English and Hinglish).

You will be given up to 3 videos. For each video, identify and extract EVERY specific Indian listed stock/company analyzed, recommended, evaluated, or discussed in that video.

For each stock, extract:
1. "company": The official commercial English name of the company (e.g. "HDFC Bank", "CAMS", "CDSL", "Tata Motors", "Infosys", "Bajaj Finance", "Pidilite", "Zomato", "Nykaa", "Reliance Industries", "Asian Paints", "ITC", "Trent", "Polycab").
2. "view": The speaker's overall stance - MUST be strictly one of: "Positive", "Negative", or "Neutral".
3. "growth_reasons": Detailed thesis, business model moat, valuation rationale, P/E metrics, ROE/ROCE, margin trends, sales growth, revenue targets, macro catalysts, or specific risks discussed by Akshat.
4. "promoter_details": Details mentioned regarding promoters, management quality, corporate governance, capital allocation, or insider holding. If not explicitly discussed, write "Not explicitly discussed in video".
5. "host_disclosed_holding": Boolean true or false. True ONLY if Akshat explicitly discloses on camera that HE HIMSELF personally bought, holds, invested in, or sold shares of this company for his personal portfolio or family account (e.g., "I hold this in my portfolio", "I bought shares of", "I am invested in", "I added more", "In my own portfolio", "I own this stock").
6. "disclosure_quote": If host_disclosed_holding is true, provide the exact verbatim spoken sentence/quote where he states his personal ownership. If false, leave as empty string "".

RULES:
- Do NOT extract general macroeconomic indices (Nifty, Sensex, Bank Nifty, S&P 500, Nasdaq).
- Do NOT extract mutual funds (e.g. Parag Parikh Flexi Cap) as individual stocks, unless an underlying equity company is being analyzed.
- Do NOT extract crypto/commodities (Bitcoin, Gold, Silver) as equity stocks.
- If a video is purely about personal budgeting, career, real estate, general life advice, or macro without analyzing any individual listed stock, return an empty list: [] for that video.
- Output MUST be a valid, parseable JSON dictionary where keys are the respective video IDs:
{
  "VIDEO_ID_1": [ { ... } ],
  "VIDEO_ID_2": [ { ... } ]
}
No markdown fences. Raw JSON only.
"""

def clean_json_response(text: str) -> dict:
    text = text.strip()
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    text = text.strip()
    try:
        return json.loads(text)
    except Exception:
        cleaned = re.sub(r',\s*([\]}])', r'\1', text)
        return json.loads(cleaned)

MODELS = [
    "gemini-3.5-flash-lite",
    "gemini-3.6-flash",
    "gemini-3.7-flash",
    "gemini-3.1-flash-lite",
    "gemini-flash-latest",
    "gemini-2.5-flash-lite",
    "gemini-3.8-flash"
]

def main():
    # Only target videos with transcripts available
    pending_videos = []
    for v in all_vids:
        vid = v['video_id']
        if vid not in extractions:
            txt_path = os.path.join(CACHE_DIR, f"{vid}.txt")
            if os.path.exists(txt_path) and os.path.getsize(txt_path) > 100:
                pending_videos.append(v)

    print(f"Total videos in manifest: {len(all_vids)}")
    print(f"Already extracted: {len(extractions)}")
    print(f"Pending to extract with transcripts: {len(pending_videos)}")

    BATCH_SIZE = 3
    for b_idx in range(0, len(pending_videos), BATCH_SIZE):
        batch = pending_videos[b_idx:b_idx+BATCH_SIZE]
        vids_in_batch = [b['video_id'] for b in batch]

        prompt_parts = ["Analyze the following videos and extract stock mentions according to the instructions:\n"]
        for b in batch:
            vid = b['video_id']
            date = b['date']
            title = b['title']
            txt_path = os.path.join(CACHE_DIR, f"{vid}.txt")
            with open(txt_path, "r", encoding="utf-8") as tf:
                t_text = tf.read()
            prompt_parts.append(f"--- VIDEO ID: {vid} ---\nTitle: {title}\nDate: {date}\nTranscript:\n{t_text[:20000]}\n--- END VIDEO {vid} ---\n")

        full_prompt = "\n".join(prompt_parts)
        print(f"[{b_idx+1}/{len(pending_videos)}] Processing Batch: {vids_in_batch}...", end=" ", flush=True)

        success = False
        for model_name in MODELS:
            try:
                time.sleep(2.0)
                response = client.models.generate_content(
                    model=model_name,
                    contents=full_prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=SYSTEM_INSTRUCTION,
                        response_mime_type="application/json"
                    )
                )

                parsed_dict = clean_json_response(response.text)

                for b in batch:
                    vid = b['video_id']
                    stocks_for_vid = parsed_dict.get(vid, [])
                    if isinstance(stocks_for_vid, dict):
                        stocks_for_vid = [stocks_for_vid]
                    extractions[vid] = {
                        "video_id": vid,
                        "title": b['title'],
                        "date": b['date'],
                        "stocks": stocks_for_vid
                    }

                # Save incrementally
                with open(OUTPUT_FILE, "w", encoding="utf-8") as out_f:
                    json.dump(extractions, out_f, indent=2, ensure_ascii=False)

                total_batch_stocks = sum(len(extractions[v]['stocks']) for v in vids_in_batch)
                print(f"-> SUCCESS via {model_name} ({total_batch_stocks} total stocks across batch)")
                success = True
                break
            except Exception as e:
                print(f"[{model_name} err: {e}]", end=" ", flush=True)
                time.sleep(3)

        if not success:
            print(f"\nFailed batch {vids_in_batch}")

    print(f"\nExtraction completed! Processed {len(extractions)} total videos saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
