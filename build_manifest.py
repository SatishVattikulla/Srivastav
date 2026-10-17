import json
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

MANIFEST_FILE = "video_manifest.json"

manifest = {}
if os.path.exists(MANIFEST_FILE):
    try:
        with open(MANIFEST_FILE, "r", encoding="utf-8") as f:
            manifest = json.load(f)
        print(f"Loaded existing manifest with {len(manifest)} videos.")
    except Exception:
        manifest = {}

with open("channel_videos.json", "r", encoding="utf-8") as f:
    entries = json.load(f)["entries"]

session = requests.Session()
retries = Retry(total=3, backoff_factor=0.3, status_forcelist=[500, 502, 503, 504])
session.mount('https://', HTTPAdapter(max_retries=retries, pool_connections=20, pool_maxsize=20))
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36',
    'Accept-Language': 'en-US,en;q=0.9'
})

pending_entries = [e for e in entries if e['id'] not in manifest or not manifest[e['id']].get('date')]
print(f"Total entries: {len(entries)}. Already resolved: {len(manifest)}. Pending: {len(pending_entries)}")

def fetch_video_meta(entry):
    vid = entry['id']
    title = entry.get('title', '')
    duration = entry.get('duration', 0)
    
    url = f"https://www.youtube.com/watch?v={vid}"
    date_str = None
    try:
        resp = session.get(url, timeout=6)
        if resp.status_code == 200:
            m = re.search(r'itemprop="datePublished" content="([^"T]+)', resp.text)
            if m:
                date_str = m.group(1)
            else:
                m2 = re.search(r'"publishDate":\s*"([^"T]+)', resp.text)
                if m2:
                    date_str = m2.group(1)
    except Exception as ex:
        pass
        
    return vid, title, duration, date_str

if pending_entries:
    count = 0
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(fetch_video_meta, e): e for e in pending_entries}
        for future in as_completed(futures):
            vid, title, duration, date_str = future.result()
            if not date_str:
                date_str = "2023-01-01" # fallback if blocked
            manifest[vid] = {
                "video_id": vid,
                "title": title,
                "date": date_str,
                "upload_date": date_str,
                "duration": duration
            }
            count += 1
            if count % 50 == 0 or count == len(pending_entries):
                print(f"Progress: {count}/{len(pending_entries)} resolved.")
                with open(MANIFEST_FILE, "w", encoding="utf-8") as f:
                    json.dump(manifest, f, indent=2, ensure_ascii=False)

with open(MANIFEST_FILE, "w", encoding="utf-8") as f:
    json.dump(manifest, f, indent=2, ensure_ascii=False)

print(f"All done! Manifest now has {len(manifest)} videos.")
