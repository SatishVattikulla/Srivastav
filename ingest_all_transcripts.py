import io
import sys
import os
import json
import time
import re
import http.cookiejar
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
from youtube_transcript_api import YouTubeTranscriptApi

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

MANIFEST_FILE = "video_manifest.json"
CACHE_DIR = "transcripts_cache"
COOKIES_FILE = "cookies.txt"

os.makedirs(CACHE_DIR, exist_ok=True)

with open(MANIFEST_FILE, "r", encoding="utf-8") as f:
    manifest = json.load(f)

# Investing priority pattern
kw = re.compile(r'stock|share|invest|portfolio|buy|bought|multibagger|dividend|nifty|market|crore|wealth|monopoly|pe|small cap|mid cap|large cap|valuation|tata|reliance|itc|hdfc|bajaj|cams|cdsl|zomato|nykaa|paytm|crash|correction|rally|growth|fund|etf|sector|recession|money', re.I)

# Sort: priority match first, then date descending
all_videos = list(manifest.values())
all_videos.sort(key=lambda x: (1 if kw.search(x.get('title', '')) else 0, x.get('date', '')), reverse=True)

print(f"Total manifest videos: {len(all_videos)}")

# Set up authenticated session
jar = http.cookiejar.MozillaCookieJar(COOKIES_FILE)
try:
    jar.load(ignore_discard=True, ignore_expires=True)
except Exception:
    pass

session = requests.Session()
session.cookies = jar
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36'
})

api = YouTubeTranscriptApi(http_client=session)

def process_video(v):
    vid = v['video_id']
    txt_path = os.path.join(CACHE_DIR, f"{vid}.txt")
    seg_path = os.path.join(CACHE_DIR, f"{vid}_segments.json")

    if os.path.exists(txt_path) and os.path.getsize(txt_path) > 100:
        return vid, "CACHED", 0, 0

    try:
        tlist = api.list(vid)
        transcript = None
        for lang in ['en', 'hi', 'en-IN']:
            try:
                transcript = tlist.find_transcript([lang])
                break
            except Exception:
                pass
        if not transcript:
            try:
                transcript = tlist.find_generated_transcript(['en', 'hi', 'en-IN'])
            except Exception:
                avail = list(tlist)
                if avail:
                    transcript = avail[0]

        if not transcript:
            return vid, "NO_TRANSCRIPT", 0, 0

        data = transcript.fetch()
        seg_data = []
        full_text_parts = []
        for item in data:
            if hasattr(item, 'text'):
                t_str = item.text
                start = getattr(item, 'start', 0)
                duration = getattr(item, 'duration', 0)
            else:
                t_str = item.get('text', '')
                start = item.get('start', 0)
                duration = item.get('duration', 0)
            seg_data.append({"start": start, "duration": duration, "text": t_str})
            full_text_parts.append(t_str)

        full_text = " ".join(full_text_parts)

        with open(txt_path, "w", encoding="utf-8") as tf:
            tf.write(full_text)
        with open(seg_path, "w", encoding="utf-8") as sf:
            json.dump(seg_data, sf, ensure_ascii=False)

        return vid, "SUCCESS", len(seg_data), len(full_text)
    except Exception as e:
        return vid, f"ERROR", 0, 0

def main():
    pending = [v for v in all_videos if not (os.path.exists(os.path.join(CACHE_DIR, f"{v['video_id']}.txt")) and os.path.getsize(os.path.join(CACHE_DIR, f"{v['video_id']}.txt")) > 100)]
    print(f"Total: {len(all_videos)} | Pending: {len(pending)}")
    
    success_cnt = 0
    fail_cnt = 0
    
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {executor.submit(process_video, v): v for v in pending}
        done_cnt = 0
        for future in as_completed(futures):
            v = futures[future]
            vid, status, segs, chars = future.result()
            done_cnt += 1
            if status == "SUCCESS":
                success_cnt += 1
                if success_cnt % 20 == 0:
                    print(f"[{done_cnt}/{len(pending)}] Fetched: {success_cnt} transcripts...")
            elif status != "CACHED":
                fail_cnt += 1
                
            if done_cnt % 100 == 0 or done_cnt == len(pending):
                print(f"Status: {done_cnt}/{len(pending)} checked. Fetched: {success_cnt}, No transcript: {fail_cnt}")

    print(f"\nIngestion complete! Fetched {success_cnt} transcripts. No transcript / unavailable: {fail_cnt}")

if __name__ == "__main__":
    main()
