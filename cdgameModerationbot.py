import sqlite3
import random
import time
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

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
COOLDOWN_MINUTES = 20  # Таймер на пиво

# =========================
# Команды
# =========================

async def pivo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    now = time.time()
    username = user.username or user.first_name

    cursor.execute("SELECT * FROM players WHERE user_id=?", (user.id,))
    row = cursor.fetchone()

    if row:
        last_drink = row[5]
        if now - last_drink < COOLDOWN_MINUTES * 60:
            minutes_left = int((COOLDOWN_MINUTES*60 - (now - last_drink)) / 60)
            await update.message.reply_text(f"⏳ Можно выпить снова через: {minutes_left} мин.")
            return
        new_beer = random.randint(1, 3)
        cursor.execute("UPDATE players SET beer = beer + ?, last_drink=? WHERE user_id=?",
                       (new_beer, now, user.id))
    else:
        new_beer = random.randint(1, 3)
        cursor.execute("INSERT INTO players (user_id, username, beer, last_drink) VALUES (?, ?, ?, ?)",
                       (user.id, username, new_beer, now))
    conn.commit()
    await update.message.reply_text(f"@{username} выпил {new_beer} л пива! 🍺")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    username = user.username or user.first_name

    cursor.execute("SELECT victories, defeats, beer, last_drink FROM players WHERE user_id=?", (user.id,))
    row = cursor.fetchone()
    if not row:
        await update.message.reply_text(f"Вы ещё не пили пиво! Напишите /пиво чтобы начать. 🍺")
        return
    victories, defeats, beer, last_drink = row
    now = time.time()
    remaining = max(0, int((COOLDOWN_MINUTES*60 - (now - last_drink))/60))
    await update.message.reply_text(f"""
📊 Статистика игрока @{username} 📊
🏆 Победы: {victories}
💀 Поражения: {defeats}
🍻 Всего выпито пива: {beer} л
⏳ Можно выпить снова через: {remaining} мин.
""")

async def add_rating(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        await update.message.reply_text("❌ Только админ может использовать эту команду.")
        return
    if len(context.args) != 2:
        await update.message.reply_text("❌ Использование: /add_rating @username количество")
        return
    target_username = context.args[0].lstrip("@")
    try:
        amount = int(context.args[1])
    except:
        await update.message.reply_text("❌ Количество должно быть числом.")
        return
    cursor.execute("SELECT * FROM players WHERE username=?", (target_username,))
    row = cursor.fetchone()
    if row:
        cursor.execute("UPDATE players SET beer = beer + ? WHERE username=?", (amount, target_username))
    else:
        cursor.execute("INSERT INTO players (username, beer) VALUES (?, ?)", (target_username, amount))
    conn.commit()
    await update.message.reply_text(f"✅ @{target_username} теперь имеет +{amount} л пива!")

async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        await update.message.reply_text("❌ Только админ может использовать эту команду.")
        return
    if not context.args:
        await update.message.reply_text("❌ Использование: /reset @username")
        return
    target_username = context.args[0].lstrip("@")
    cursor.execute("SELECT * FROM players WHERE username=?", (target_username,))
    row = cursor.fetchone()
    if not row:
        await update.message.reply_text(f"Игрок @{target_username} не найден.")
        return
    cursor.execute("""
        UPDATE players SET victories=0, defeats=0, beer=0, last_drink=0 WHERE username=?
    """, (target_username,))
    conn.commit()
    await update.message.reply_text(f"✅ Статистика @{target_username} успешно сброшена!")

async def top(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cursor.execute("SELECT username, beer FROM players ORDER BY beer DESC LIMIT 5")
    rows = cursor.fetchall()
    if not rows:
        await update.message.reply_text("Нет данных по игрокам. 🍺")
        return
    message = "🌟 ТОП-5 ИГРОКОВ ПИВНОЙ ДУЭЛИ 🌟\n\n"
    for i, (username, beer) in enumerate(rows, 1):
        message += f"{i}. 🍺 @{username}\n   🍻 Выпито: {beer} л\n\n"
    await update.message.reply_text(message)

# =========================
# Основная функция
# =========================
def main():
    app = ApplicationBuilder().token("8319716433:AAEXgzUiJKixoJKMw-Y1pVGUbw5yXR8-YgE").build()

    app.add_handler(CommandHandler(["pivo", "пиво"], pivo))
    app.add_handler(CommandHandler(["status", "статус"], status))
    app.add_handler(CommandHandler("add_rating", add_rating))
    app.add_handler(CommandHandler("reset", reset))
    app.add_handler(CommandHandler(["top", "топ"], top))

    app.run_polling()

if __name__ == "__main__":
    main()
