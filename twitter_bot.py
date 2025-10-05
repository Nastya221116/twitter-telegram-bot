import os
import time
import json
import threading
import requests
from telegram import Update, Bot
from telegram.ext import Updater, CommandHandler, CallbackContext

# === НАСТРОЙКИ ===
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = int(os.getenv("CHAT_ID"))
TWITTER_BEARER_TOKEN = os.getenv("TWITTER_BEARER_TOKEN")

DATA_FILE = "twitter_users.json"
CHECK_INTERVAL = 30  # каждые 30 секунд

bot = Bot(token=BOT_TOKEN)


# === РАБОТА С ДАННЫМИ ===
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {"users": [], "last_ids": {}}


def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)


# === ПРОВЕРКА ПОДКЛЮЧЕНИЯ К TWITTER API ===
def test_twitter_api():
    url = "https://api.twitter.com/2/users/by/username/elonmusk"
    headers = {"Authorization": f"Bearer {TWITTER_BEARER_TOKEN}"}
    resp = requests.get(url, headers=headers)
    if resp.status_code == 200:
        print("✅ Twitter API connection OK")
        return True
    else:
        print(f"❌ Twitter API error: {resp.status_code} — {resp.text}")
        return False


# === ПОЛУЧЕНИЕ ПОСЛЕДНЕГО ТВИТА ===
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
            print(f"📥 Последний твит @{user}: {tweet['text'][:60]}...")
            return tweet

        print(f"⏳ У @{user} нет новых твитов")
        return None

    except Exception as e:
        print(f"❌ Ошибка при получении @{user}: {e}")
        return None


# === ПРОВЕРКА НОВЫХ ТВИТОВ ===
def check_new_tweets():
    data = load_data()
    print("✅ Бот запущен и проверяет Twitter каждые 30 секунд...")

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

        time.sleep(CHECK_INTERVAL)


# === TELEGRAM КОМАНДЫ ===
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


# === ОСНОВНОЙ ЗАПУСК ===
def main():
    if not test_twitter_api():
        print("❌ Остановка: Twitter API не отвечает.")
        return

    updater = Updater(BOT_TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("add", add_user))
    dp.add_handler(CommandHandler("list", list_users))
    dp.add_handler(CommandHandler("status", status))

    # запускаем поток проверки твитов
    threading.Thread(target=check_new_tweets, daemon=True).start()

    # используем polling, а не webhook (работает в Free-версии)
    print("🌐 Telegram polling запущен...")
    updater.start_polling()
    updater.idle()


if __name__ == "__main__":
    main()
