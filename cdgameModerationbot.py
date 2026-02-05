import random
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler, MessageHandler, filters

TOKEN = "8349946765:AAG31kDyeywXsYk1z3GZMJ19J8BkkxpgVvQ"

# ------------------- Хранилище -------------------
users = {}  # user_id -> персонаж
items = {1: {"name": "Меч новичка", "price": 100}, 2: {"name": "Щит новичка", "price": 100}}
monsters = [{"name": "Гоблин", "hp": 20, "xp": 10, "coins": 20}, {"name": "Волк", "hp": 30, "xp": 20, "coins": 40}]

# ------------------- Команды -------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in users:
        users[user_id] = {"name": update.effective_user.first_name, "level":1, "hp":100, "xp":0, "coins":100, "inventory":[]}
        await update.message.reply_text(f"Привет, {update.effective_user.first_name}! Ваш RPG-персонаж создан.")
    else:
        await update.message.reply_text("Вы уже создали персонажа!")

async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in users:
        await update.message.reply_text("Сначала создайте персонажа через /start")
        return
    user = users[user_id]
    inv = ", ".join([items[i]["name"] for i in user["inventory"]]) or "Пусто"
    text = f"👤 {user['name']}\n💎 Уровень: {user['level']}\n❤️ HP: {user['hp']}\n✨ XP: {user['xp']}\n💰 Монеты: {user['coins']}\n🎒 Инвентарь: {inv}"
    await update.message.reply_text(text)

async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Бой с монстром", callback_data="fight")],
        [InlineKeyboardButton("Магазин", callback_data="shop")]
    ]
    await update.message.reply_text("Главное меню:", reply_markup=InlineKeyboardMarkup(keyboard))

# ------------------- Callback -------------------
async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    if user_id not in users:
        await query.edit_message_text("Сначала создайте персонажа через /start")
        return
    user = users[user_id]

    # ------------------- Fight -------------------
    if query.data == "fight":
        monster = random.choice(monsters)
        dmg = random.randint(5, 15)
        monster_hp = monster["hp"] - dmg
        result = f"Вы сражаетесь с {monster['name']} и наносите {dmg} урона.\n"
        if monster_hp <= 0:
            user["xp"] += monster["xp"]
            user["coins"] += monster["coins"]
            result += f"Монстр побежден! Получено {monster['xp']} XP и {monster['coins']} монет."
        else:
            result += f"{monster['name']} остался жив с {monster_hp} HP."
        await query.edit_message_text(result)

    # ------------------- Shop -------------------
    elif query.data == "shop":
        keyboard = [
            [InlineKeyboardButton(f"{i['name']} - {i['price']} 💰", callback_data=f"buy:{item_id}")]
            for item_id, i in items.items()
        ]
        await query.edit_message_text("Магазин:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif query.data.startswith("buy:"):
        _, item_id = query.data.split(":")
        item_id = int(item_id)
        item = items[item_id]
        if user["coins"] >= item["price"]:
            user["coins"] -= item["price"]
            user["inventory"].append(item_id)
            await query.edit_message_text(f"Вы купили {item['name']}!")
        else:
            await query.edit_message_text("Недостаточно монет!")

# ------------------- Запуск -------------------
app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("profile", profile))
app.add_handler(CommandHandler("menu", menu))
app.add_handler(CallbackQueryHandler(callback_handler))
app.add_handler(MessageHandler(filters.ALL, lambda update, context: None))  # заглушка

print("RPG бот с кнопками запущен...")
app.run_polling()
