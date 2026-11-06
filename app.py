import os
import sqlite3
from flask import Flask, request, jsonify

app = Flask(__name__)

TOKEN = os.environ.get("BOT_TOKEN")
DB = "/var/data/music.db"

def init_db():
    os.makedirs("/var/data", exist_ok=True)
    with sqlite3.connect(DB) as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS songs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                file_id TEXT
            )
        """)

@app.route("/")
def home():
    return "Music bot is running!"

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json or {}
    message = data.get("message", {})
    audio = message.get("audio") or message.get("document")

    if audio and audio.get("file_id"):
        title = audio.get("title") or audio.get("file_name") or "Без названия"
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
    return jsonify([{"id": r[0], "title": r[1]} for r in rows])

if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
