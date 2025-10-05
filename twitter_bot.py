import os
import time
import json
import threading
import requests
from telegram import Update, Bot
from telegram.ext import Updater, CommandHandler, CallbackContext

# === Настройки ===
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = int(os.getenv("CHAT_ID"))
TWITTER_BEARER_TOKEN = os.getenv("TWITTER_BEARER_TOKEN")

DATA_FILE = "twitter_users.json"
CHECK_INTERVAL = 30  # каждые 30 секунд

bot = Bot(token=BOT_TOKEN)

# === Работа с данными ===
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {"users": [], "last_ids": {}}

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

# === Получение последнего твита ===
def get_latest_tweet(user):
    try:
        headers = {"Authorization": f"Bearer {TWITTER_BEARER_TOKEN}"}

        # Получаем ID пользователя
        user_url = f"https://api.twitter.com/2/users/by/username/{user}"
        user_resp = requests.get(user_url, headers=headers).json()

        if "data" not in user_resp:
            print(f"⚠️ Не найден пользователь @{user}")
            return None

        user_id = user_resp["data"]["id"]

        # Получаем последние твиты
        tweets_url = (
            f"https://api.twitter.com/2/users/{user_id}/tweets?max_results=5"
            f"&tweet.fields=created_at,text,id"
        )
        tweets_resp = requests.get(tweets_url, headers=headers).json()

        if "data" in tweets_resp and len(tweets_resp["data"]) > 0:
            tweet = tweets_resp["data"][0]
            return tweet

        return None
    except Exception as e:
        print(f"❌ Ошибка при получении @{user}: {e}")
        return None

# === Проверка новых твитов ===
def check_new_tweets():
    data = load_data()
    print("✅ Bot started successfully and checking Twitter every 30 seconds...")

    while True:
        for user in data["users"]:
            tweet = get_latest_tweet(user)
            if not tweet:
                continue

            tweet_id = str(tweet["id"])
            last_id = data["last_ids"].get(user)

            if last_id != tweet_id:
                msg = (
                    f"🕊 Новый твит от @{user}:\n\n"
                    f"{tweet['text']}\n\n"
                    f"🔗 https://x.com/{user}/status/{tweet['id']}"
                )
                try:
                    bot.send_message(chat_id=CHAT_ID, text=msg)
                    print(f"📨 Отправлен твит @{user}")
                except Exception as e:
                    print(f"⚠️ Ошибка отправки сообщения: {e}")
                data["last_ids"][user] = tweet_id
                save_data(data)
            else:
                print(f"⏳ У @{user} нет новых твитов")

        time.sleep(CHECK_INTERVAL)

# === Команды Telegram ===
def start(update: Update, context: CallbackContext):
    update.message.reply_text(
        "👋 Привет! Я бот, который присылает новые твиты.\n\n"
        "Команды:\n"
        "/add username — добавить пользователя\n"
        "/list — список отслеживаемых\n"
        "/status — состояние бота"
    )

def add_user(update: Update, context: CallbackContext):
    data = load_data()
    if len(context.args) == 0:
        update.message.reply_text("❗ Используй: /add имя_пользователя (без @)")
        return
    user = context.args[0].replace("@", "")
    if user not in data["users"]:
        data["users"].append(user)
        save_data(data)
        update.message.reply_text(f"✅ Теперь отслеживаю @{user}\n🔗 https://x.com/{user}")
    else:
        update.message.reply_text(f"⚠️ @{user} уже добавлен.\n🔗 https://x.com/{user}")

def list_users(update: Update, context: CallbackContext):
    data = load_data()
    if not data["users"]:
        update.message.reply_text("Список пуст. Добавь кого-то через /add")
        return
    users_list = "\n".join([f"@{u} → https://x.com/{u}" for u in data["users"]])
    update.message.reply_text(f"📋 Отслеживаемые пользователи:\n{users_list}")

def status(update: Update, context: CallbackContext):
    data = load_data()
    count = len(data["users"])
    update.message.reply_text(
        f"🟢 Бот работает.\nПроверяет {count} пользователей каждые {CHECK_INTERVAL} сек."
    )

# === Основная функция (webhook для Render) ===
def main():
    updater = Updater(BOT_TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("add", add_user))
    dp.add_handler(CommandHandler("list", list_users))
    dp.add_handler(CommandHandler("status", status))

    threading.Thread(target=check_new_tweets, daemon=True).start()

    PORT = int(os.environ.get("PORT", "10000"))
    RENDER_URL = f"https://{os.environ['RENDER_EXTERNAL_HOSTNAME']}/{BOT_TOKEN}"

    print(f"🌐 Starting webhook on {RENDER_URL}")
    updater.start_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path=BOT_TOKEN,
        webhook_url=RENDER_URL,
    )
    updater.idle()

if __name__ == "__main__":
    main()
