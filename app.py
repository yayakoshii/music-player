import os
import sqlite3
import requests
from flask import Flask, request, jsonify, Response

app = Flask(__name__)

TOKEN = os.environ.get("BOT_TOKEN")
DB = "/tmp/music.db"

def init_db():
    with sqlite3.connect(DB) as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS songs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                file_id TEXT
            )
        """)

init_db()

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
        with sqlite3.connect(DB) as con:
            con.execute(
                "INSERT INTO songs (title, file_id) VALUES (?, ?)",
                (title, audio["file_id"])
            )

    return jsonify({"ok": True})

@app.route("/songs")
def songs():
    with sqlite3.connect(DB) as con:
        rows = con.execute(
            "SELECT id, title FROM songs ORDER BY id DESC"
        ).fetchall()
    return jsonify([
        {"id": r[0], "title": r[1], "url": f"/stream/{r[0]}"}
        for r in rows
    ])

@app.route("/stream/<int:song_id>")
def stream(song_id):
    if not TOKEN:
        return "Bot token not configured", 500

    with sqlite3.connect(DB) as con:
        row = con.execute(
            "SELECT file_id FROM songs WHERE id = ?",
            (song_id,)
        ).fetchone()

    if not row:
        return "Song not found", 404

    info = requests.get(
        f"https://api.telegram.org/bot{TOKEN}/getFile",
        params={"file_id": row[0]}
    ).json()

    if not info.get("ok"):
        return "Telegram file error", 502

    path = info["result"]["file_path"]
    audio = requests.get(
        f"https://api.telegram.org/file/bot{TOKEN}/{path}",
        stream=True
    )

    return Response(
        audio.iter_content(65536),
        content_type=audio.headers.get(
            "Content-Type", "audio/mpeg"
        )
    )
