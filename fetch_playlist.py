import sys
import json
import yt_dlp

print("Extracting playlist entries for Akshat Shrivastava...")
ydl_opts = {
    'extract_flat': 'in_playlist',
    'skip_download': True,
    'quiet': False
}

playlist_url = "https://www.youtube.com/playlist?list=UUqW8jxh4tH1Z1sWPbkGWL4g"

with yt_dlp.YoutubeDL(ydl_opts) as ydl:
    info = ydl.extract_info(playlist_url, download=False)

entries = info.get('entries', [])
print(f"Total entries fetched: {len(entries)}")

with open("channel_videos.json", "w", encoding="utf-8") as f:
    json.dump({"entries": entries}, f, indent=2, ensure_ascii=False)

print("Saved channel_videos.json successfully.")
