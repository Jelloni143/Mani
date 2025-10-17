import os
import tempfile
import re
import requests
from yt_dlp import YoutubeDL
from flask import Flask, request

app = Flask(__name__)

# ---------- CONFIG ----------
BOT_TOKEN = os.environ.get("BOT_TOKEN")  # Render environment variable
API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"
TG_FILE_LIMIT = 50 * 1024 * 1024  # 50 MB
YTDL_OPTS = {
    "format": "bestvideo[height<=720]+bestaudio/best",
    "noplaylist": True,
    "quiet": True,
    "no_warnings": True,
    "merge_output_format": "mp4",
    "outtmpl": "%(id)s.%(ext)s",
}
URL_REGEX = re.compile(r"(https?://[^\s]+)")
# -----------------------------

def send_message(chat_id, text):
    try:
        requests.post(f"{API_URL}/sendMessage", data={"chat_id": chat_id, "text": text, "parse_mode": "HTML"})
    except Exception as e:
        print("send_message error:", e)

def extract_url(text):
    if not text:
        return None
    m = URL_REGEX.search(text)
    return m.group(1) if m else None

def download_video(url, tmpdir):
    opts = YTDL_OPTS.copy()
    opts["outtmpl"] = os.path.join(tmpdir, "%(id)s.%(ext)s")
    try:
        with YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
            if "entries" in info:
                info = info["entries"][0]
            for fname in os.listdir(tmpdir):
                return os.path.join(tmpdir, fname), info
        return None, "No file found"
    except Exception as e:
        return None, str(e)

def send_document(chat_id, file_path, caption=None):
    try:
        with open(file_path, "rb") as f:
            files = {"document": (os.path.basename(file_path), f)}
            data = {"chat_id": chat_id}
            if caption:
                data["caption"] = caption
            r = requests.post(f"{API_URL}/sendDocument", data=data, files=files)
            return r.ok
    except Exception as e:
        print("send_document error:", e)
        return False

@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():
    update = request.get_json()
    msg = update.get("message")
    if not msg:
        return "ok"
    chat_id = msg["chat"]["id"]
    text = msg.get("text") or msg.get("caption") or ""
    username = msg.get("from", {}).get("username") or msg.get("from", {}).get("first_name")
    print(f"Message from {username} ({chat_id}): {text[:60]}")

    if text.strip().startswith("/start"):
        send_message(chat_id, "🌌 Axel Downloader ready.\nSend a YouTube or Instagram video link and I'll download it for you.")
        return "ok"

    url = extract_url(text)
    if not url:
        send_message(chat_id, "Koi valid YouTube/Instagram link bhejo.")
        return "ok"

    send_message(chat_id, "Link mil gaya — download start kar raha hoon. Thoda time lag sakta hai.")

    with tempfile.TemporaryDirectory() as tmpdir:
        filepath, info = download_video(url, tmpdir)
        if filepath:
            send_document(chat_id, filepath, caption=info.get("title"))
        else:
            send_message(chat_id, f"Download failed: {info}")

    return "ok"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
