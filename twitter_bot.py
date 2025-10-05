import os
import time
import json
import snscrape.modules.twitter as sntwitter
from telegram import Update, Bot
from telegram.ext import Updater, CommandHandler, CallbackContext
import threading

# Настройки
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = int(os.getenv("CHAT_ID"))
DATA_FILE = "twitter_users.json"
CHECK_INTERVAL = 60  # сек

bot = Bot(token=BOT_TOKEN)

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {"users": [], "last_ids": {}}

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

def get_latest_tweet(user):
    try:
        for tweet in sntwitter.TwitterUserScraper(user).get_items():
            return tweet
    except Exception as e:
        print(f"❌ Ошибка при получении @{user}: {e}")
        return None

def check_new_tweets():
    data = load_data()
    print("✅ Bot started successfully and checking Twitter every minute...")
    while True:
        for user in data["users"]:
            tweet = get_latest_tweet(user)
            if not tweet:
                continue
            tweet_id = str(tweet.id)
            if data["last_ids"].get(user) != tweet_id:
                msg = (
                    f"🕊 Новый твит от @{user}:\n\n"
                    f"{tweet.content}\n\n"
                    f"🔗 https://x.com/{user}/status/{tweet.id}"
                )
                bot.send_message(chat_id=CHAT_ID, text=msg)
                data["last_ids"][user] = tweet_id
                save_data(data)
        time.sleep(CHECK_INTERVAL)

def start(update: Update, context: CallbackContext):
    update.message.reply_text(
        "👋 Привет! Я бот, который присылает новые твиты.\n\n"
        "Команды:\n"
        "/add @user — добавить пользователя\n"
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
        update.message.reply_text(
            f"✅ Теперь отслеживаю @{user}\n🔗 https://x.com/{user}"
        )
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

def main():
    updater = Updater(BOT_TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("add", add_user))
    dp.add_handler(CommandHandler("list", list_users))
    dp.add_handler(CommandHandler("status", status))

    threading.Thread(target=check_new_tweets, daemon=True).start()

    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
