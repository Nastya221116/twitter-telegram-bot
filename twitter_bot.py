import snscrape.modules.twitter as sntwitter
from telegram import Update, Bot
from telegram.ext import Updater, CommandHandler, CallbackContext
import json, time, threading, os

# === Настройки ===
BOT_TOKEN = "8087431779:AAGlIYAxhIyRg-5_oAotxFdtAyaIxqtOEoo"  # твой токен
CHAT_ID = 448275217                                               # твой Telegram ID
DATA_FILE = "twitter_users.json"                                  # файл для хранения данных

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

# === Получение твитов ===
def get_latest_tweet(user):
    try:
        for tweet in sntwitter.TwitterUserScraper(user).get_items():
            return tweet  # берём первый (последний по времени)
    except Exception as e:
        print(f"Ошибка при чтении @{user}: {e}")
        return None

# === Проверка новых твитов ===
def check_new_tweets():
    data = load_data()
    while True:
        for user in data["users"]:
            tweet = get_latest_tweet(user)
            if not tweet:
                continue
            tweet_id = str(tweet.id)
            if data["last_ids"].get(user) != tweet_id:
                text = (
                    f"🕊 Новый твит от @{user}:\n\n"
                    f"{tweet.content}\n\n"
                    f"🔗 https://x.com/{user}/status/{tweet.id}"
                )
                bot.send_message(chat_id=CHAT_ID, text=text)
                data["last_ids"][user] = tweet_id
                save_data(data)
        time.sleep(30)  # проверка каждые 1 минут

# === Команды Telegram ===
def add_user(update: Update, context: CallbackContext):
    data = load_data()
    if len(context.args) == 0:
        update.message.reply_text("❗ Используй: /add имя_пользователя (без @)")
        return
    user = context.args[0].replace("@", "")
    if user not in data["users"]:
        data["users"].append(user)
        save_data(data)
        update.message.reply_text(f"✅ Пользователь @{user} добавлен!")
    else:
        update.message.reply_text("⚠️ Этот пользователь уже добавлен.")

def list_users(update: Update, context: CallbackContext):
    data = load_data()
    if not data["users"]:
        update.message.reply_text("Список пуст. Добавь кого-то через /add")
        return
    users_list = "\n".join([f"@{u}" for u in data["users"]])
    update.message.reply_text(f"📋 Отслеживаемые пользователи:\n{users_list}")

def start(update: Update, context: CallbackContext):
    update.message.reply_text(
        "👋 Привет! Я бот, который присылает новые твиты.\n\n"
        "Команды:\n"
        "/add @user — добавить пользователя\n"
        "/list — показать список\n"
    )

# === Запуск бота ===
def main():
    updater = Updater(BOT_TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("add", add_user))
    dp.add_handler(CommandHandler("list", list_users))

    # Запускаем фоновую проверку твитов
    threading.Thread(target=check_new_tweets, daemon=True).start()

    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
