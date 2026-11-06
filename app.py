import os
import requests
from flask import Flask, request, jsonify, Response

app = Flask(__name__)

TOKEN = os.environ.get("BOT_TOKEN")
SUPABASE_URL = os.environ.get("SUPABASE_URL", "").rstrip("/")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

HEADERS = {
    "apikey": SUPABASE_KEY or "",
    "Content-Type": "application/json"
}


@app.after_request
def cors(response):
    response.headers["Access-Control-Allow-Origin"] = (
        "https://yayakoshii.github.io"
    )
    return response


@app.route("/")
def home():
    return "Music bot is running!"


@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json or {}
    message = data.get("message", {})
    audio = message.get("audio")

    if audio and audio.get("file_id"):
        title = audio.get("title") or "Без названия"

        result = requests.post(
            f"{SUPABASE_URL}/rest/v1/songs",
            headers={
                **HEADERS,
                "Prefer": "return=minimal"
            },
            json={
                "title": title,
                "file_id": audio["file_id"]
            },
            timeout=20
        )

        if not result.ok:
            return jsonify({"error": "Database error"}), 500

    return jsonify({"ok": True})


@app.route("/songs")
def songs():
    result = requests.get(
        f"{SUPABASE_URL}/rest/v1/songs",
        headers=HEADERS,
        params={
            "select": "id,title",
            "order": "id.desc"
        },
        timeout=20
    )

    if not result.ok:
        return jsonify({"error": "Database error"}), 500

    return jsonify([
        {
            "id": song["id"],
            "title": song["title"],
            "url": f"/stream/{song['id']}"
        }
        for song in result.json()
    ])


@app.route("/stream/<int:song_id>")
def stream(song_id):
    if not TOKEN:
        return "Bot token not configured", 500

    result = requests.get(
        f"{SUPABASE_URL}/rest/v1/songs",
        headers=HEADERS,
        params={
            "select": "file_id",
            "id": f"eq.{song_id}"
        },
        timeout=20
    )

    if not result.ok:
        return "Database error", 500

    items = result.json()

    if not items:
        return "Song not found", 404

    info = requests.get(
        f"https://api.telegram.org/bot{TOKEN}/getFile",
        params={"file_id": items[0]["file_id"]},
        timeout=20
    ).json()

    if not info.get("ok"):
        return "Telegram file error", 502

    path = info["result"]["file_path"]

    audio = requests.get(
        f"https://api.telegram.org/file/bot{TOKEN}/{path}",
        timeout=60
    )

    if audio.status_code != 200:
        return "Audio download error", 502

    return Response(
        audio.content,
        content_type="audio/mpeg",
        headers={
            "Content-Disposition": 'inline; filename="music.mp3"',
            "Accept-Ranges": "none"
        }
    )
