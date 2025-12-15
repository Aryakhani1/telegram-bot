import telebot
from telebot import types
from flask import Flask, request
import json
import time
import threading
import os
import traceback

# =============================
TOKEN = os.environ.get("8551450696:AAFcgHuKWjItU2Q2lXnrypnDFBAiLrx86TY")
bot = telebot.TeleBot(TOKEN)
# =============================

CHANNELS = ["@TGCryptoSignal", "@linkdoniwn", "@bass312"]
VIDEO_DB_FILE = "video_links.json"

pending_users = {}  # chat_id → key

app = Flask(__name__)

# --------------------------
def load_video_db():
    try:
        if os.path.exists(VIDEO_DB_FILE):
            with open(VIDEO_DB_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return data
    except Exception as e:
        print("JSON error:", e)
        traceback.print_exc()
    return {}

# --------------------------
def check_membership(user_id):
    for channel in CHANNELS:
        try:
            member = bot.get_chat_member(channel, user_id)
            if member.status in ["left", "kicked"]:
                return False
        except:
            return False
    return True

# --------------------------
def delete_after_delay(chat_id, msg_id, delay):
    time.sleep(delay)
    try:
        bot.delete_message(chat_id, msg_id)
    except:
        pass

# --------------------------
def send_video_by_key(chat_id, key):
    db = load_video_db()
    info = db.get(key)

    if not info:
        bot.send_message(chat_id, "❌ ویدیو یافت نشد.")
        return

    file_path = info.get("file")
    caption = info.get("caption", "")
    active_seconds = int(info.get("active_seconds", 20))

    if not file_path or not os.path.exists(file_path):
        bot.send_message(chat_id, "❌ فایل ویدیو در سرور نیست.")
        return

    with open(file_path, "rb") as f:
        msg = bot.send_video(chat_id, f, caption=caption)

    threading.Thread(
        target=delete_after_delay,
        args=(chat_id, msg.message_id, active_seconds),
        daemon=True
    ).start()

# --------------------------
def extract_key(text):
    if not text:
        return None
    if text.startswith("/start"):
        parts = text.split(" ", 1)
        if len(parts) == 2:
            return parts[1].strip().rstrip("/")
    return None

# --------------------------
@bot.message_handler(commands=["start"])
def start_handler(message):
    chat_id = message.chat.id
    key = extract_key(message.text)

    if key:
        pending_users[chat_id] = key

    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("✔️ تایید عضویت", callback_data="check_join")
    )

    text = (
        "👋 خوش اومدی\n\n"
        "برای دریافت ویدیو ابتدا عضو کانال‌ها شو:\n"
        + "\n".join(CHANNELS)
    )

    bot.send_message(chat_id, text, reply_markup=markup)

# --------------------------
@bot.callback_query_handler(func=lambda c: True)
def callback_handler(call):
    chat_id = call.message.chat.id
    user_id = call.from_user.id

    if call.data != "check_join":
        return

    if not check_membership(user_id):
        bot.answer_callback_query(call.id, "❌ هنوز عضو نیستی")
        return

    bot.answer_callback_query(call.id, "✔️ تایید شد")
    key = pending_users.get(chat_id)

    if not key:
        bot.send_message(chat_id, "❌ لینک معتبر نیست.")
        return

    send_video_by_key(chat_id, key)
    pending_users.pop(chat_id, None)

# ==========================
# WEBHOOK PART
# ==========================
@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    json_str = request.get_data().decode("UTF-8")
    update = telebot.types.Update.de_json(json_str)
    bot.process_new_updates([update])
    return "OK", 200

@app.route("/")
def index():
    return "Bot is running!"

# ==========================
if __name__ == "__main__":
    PORT = int(os.environ.get("PORT", 10000))
    WEBHOOK_URL = os.environ.get("WEBHOOK_URL")

    bot.remove_webhook()
    bot.set_webhook(url=f"{WEBHOOK_URL}/{TOKEN}")

    app.run(host="0.0.0.0", port=PORT)