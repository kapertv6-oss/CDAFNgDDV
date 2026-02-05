import sqlite3
import random
import time
from telegram import Update
from telegram.ext import Updater, CommandHandler, CallbackContext

# =========================
# Настройка базы данных
# =========================
conn = sqlite3.connect("beer_duel.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS players (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    victories INTEGER DEFAULT 0,
    defeats INTEGER DEFAULT 0,
    beer INTEGER DEFAULT 0,
    last_drink REAL DEFAULT 0
)
""")
conn.commit()

# =========================
# Настройки
# =========================
ADMIN_ID = 7652697216
COOLDOWN_MINUTES = 20  # таймер на пиво

# =========================
# Команды
# =========================

# /пиво или /pivo
def pivo(update: Update, context: CallbackContext):
    user = update.message.from_user
    now = time.time()
    username = user.username or user.first_name

    cursor.execute("SELECT * FROM players WHERE user_id=?", (user.id,))
    row = cursor.fetchone()

    if row:
        last_drink = row[5]
        if now - last_drink < COOLDOWN_MINUTES * 60:
            minutes_left = int((COOLDOWN_MINUTES*60 - (now - last_drink)) / 60)
            update.message.reply_text(f"⏳ Можно выпить снова через: {minutes_left} мин.")
            return
        new_beer = random.randint(1, 3)
        cursor.execute("UPDATE players SET beer = beer + ?, last_drink=? WHERE user_id=?",
                       (new_beer, now, user.id))
    else:
        new_beer = random.randint(1, 3)
        cursor.execute("INSERT INTO players (user_id, username, beer, last_drink) VALUES (?, ?, ?, ?)",
                       (user.id, username, new_beer, now))
    conn.commit()
    update.message.reply_text(f"@{username} выпил {new_beer} л пива! 🍺")

# /статус или /status
def status(update: Update, context: CallbackContext):
    user = update.message.from_user
    username = user.username or user.first_name

    cursor.execute("SELECT victories, defeats, beer, last_drink FROM players WHERE user_id=?", (user.id,))
    row = cursor.fetchone()
    if not row:
        update.message.reply_text(f"Вы ещё не пили пиво! Напишите /пиво чтобы начать. 🍺")
        return
    victories, defeats, beer, last_drink = row
    now = time.time()
    remaining = max(0, int((COOLDOWN_MINUTES*60 - (now - last_drink))/60))
    update.message.reply_text(f"""
📊 Статистика игрока @{username} 📊
🏆 Победы: {victories}
💀 Поражения: {defeats}
🍻 Всего выпито пива: {beer} л
⏳ Можно выпить снова через: {remaining} мин.
""")

# /add_rating — только для админа
def add_rating(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    if user_id != ADMIN_ID:
        update.message.reply_text("❌ Только админ может использовать эту команду.")
        return
    if len(context.args) != 2:
        update.message.reply_text("❌ Использование: /add_rating @username количество")
        return
    target_username = context.args[0].lstrip("@")
    try:
        amount = int(context.args[1])
    except:
        update.message.reply_text("❌ Количество должно быть числом.")
        return
    cursor.execute("SELECT * FROM players WHERE username=?", (target_username,))
    row = cursor.fetchone()
    if row:
        cursor.execute("UPDATE players SET beer = beer + ? WHERE username=?", (amount, target_username))
    else:
        cursor.execute("INSERT INTO players (username, beer) VALUES (?, ?)", (target_username, amount))
    conn.commit()
    update.message.reply_text(f"✅ @{target_username} теперь имеет +{amount} л пива!")

# /reset — сброс статистики, только для админа
def reset(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    if user_id != ADMIN_ID:
        update.message.reply_text("❌ Только админ может использовать эту команду.")
        return
    if not context.args:
        update.message.reply_text("❌ Использование: /reset @username")
        return
    target_username = context.args[0].lstrip("@")
    cursor.execute("SELECT * FROM players WHERE username=?", (target_username,))
    row = cursor.fetchone()
    if not row:
        update.message.reply_text(f"Игрок @{target_username} не найден.")
        return
    cursor.execute("""
        UPDATE players SET victories=0, defeats=0, beer=0, last_drink=0 WHERE username=?
    """, (target_username,))
    conn.commit()
    update.message.reply_text(f"✅ Статистика @{target_username} успешно сброшена!")

# /топ или /top
def top(update: Update, context: CallbackContext):
    cursor.execute("SELECT username, beer FROM players ORDER BY beer DESC LIMIT 5")
    rows = cursor.fetchall()
    if not rows:
        update.message.reply_text("Нет данных по игрокам. 🍺")
        return
    message = "🌟 ТОП-5 ИГРОКОВ ПИВНОЙ ДУЭЛИ 🌟\n\n"
    for i, (username, beer) in enumerate(rows, 1):
        message += f"{i}. 🍺 @{username}\n   🍻 Выпито: {beer} л\n\n"
    update.message.reply_text(message)

# =========================
# Основная функция
# =========================
def main():
    updater = Updater("8319716433:AAEXgzUiJKixoJKMw-Y1pVGUbw5yXR8-YgE")  # <-- вставьте токен вашего бота
    dp = updater.dispatcher

    dp.add_handler(CommandHandler(["pivo", "пиво"], pivo))
    dp.add_handler(CommandHandler(["status", "статус"], status))
    dp.add_handler(CommandHandler("add_rating", add_rating))
    dp.add_handler(CommandHandler("reset", reset))
    dp.add_handler(CommandHandler(["top", "топ"], top))

    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
