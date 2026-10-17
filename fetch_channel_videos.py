import subprocess
import sys
import os

print("Running yt-dlp with Python 3.14 to fetch @AkshatZayn/videos...")
cmd = [
    r"C:\Python314\python.exe",
    "-m", "yt_dlp",
    "--flat-playlist",
    "--dump-single-json",
    "https://www.youtube.com/@AkshatZayn/videos"
]

with open("channel_videos_v2.json", "w", encoding="utf-8") as f:
    res = subprocess.run(cmd, stdout=f, stderr=subprocess.PIPE, text=True, encoding="utf-8")

if res.returncode != 0:
    print("Error:", res.stderr)
else:
    size = os.path.getsize("channel_videos_v2.json")
    print(f"Successfully saved channel_videos_v2.json. Size: {size} bytes")
