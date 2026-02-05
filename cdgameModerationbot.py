import random
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler, MessageHandler, filters

TOKEN = "8349946765:AAG31kDyeywXsYk1z3GZMJ19J8BkkxpgVvQ"

# ------------------- Хранилище -------------------
users = {}  # user_id -> {"name":str, "level":int, "hp":int, "xp":int, "coins":int, "gems":int, "power_points":int, "inventory":[], "last_mines":datetime, "mines_played":int}
items = {
    1: {"name": "Меч новичка", "type": "weapon", "effect": 5, "price": 100},
    2: {"name": "Щит новичка", "type": "armor", "effect": 5, "price": 100}
}
monsters = [
    {"name": "Слабый гоблин", "hp": 20, "xp": 10, "coins": 20},
    {"name": "Большой волк", "hp": 30, "xp": 20, "coins": 40}
]
pvp_challenges = {}  # group_id -> {"challenger": user_id, "target": user_id}

# ------------------- Команды -------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in users:
        users[user_id] = {"name": update.effective_user.first_name, "level":1, "hp":100, "xp":0, "coins":100, "gems":10, "power_points":5, "inventory":[], "last_mines": datetime.min, "mines_played":0}
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
    text = (
        f"👤 {user['name']}\n💎 Уровень: {user['level']}\n❤️ HP: {user['hp']}\n"
        f"✨ XP: {user['xp']}\n💰 Монеты: {user['coins']}\n💎 Кристаллы: {user['gems']}\n⚡ Очки силы: {user['power_points']}\n🎒 Инвентарь: {inv}"
    )
    await update.message.reply_text(text)

async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Бой с монстром", callback_data="fight")],
        [InlineKeyboardButton("Магазин", callback_data="shop")],
        [InlineKeyboardButton("Мини-Игры", callback_data="minigames")],
        [InlineKeyboardButton("Квесты", callback_data="quests")],
        [InlineKeyboardButton("PvP", callback_data="pvp")],
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

    # ------------------- Fight с монстром -------------------
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

    # ------------------- Магазин -------------------
    elif query.data == "shop":
        keyboard = [[InlineKeyboardButton(f"{i['name']} - {i['price']} 💰", callback_data=f"buy:{item_id}")] for item_id, i in items.items()]
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

    # ------------------- Мини-игры -------------------
    elif query.data == "minigames":
        keyboard = [[InlineKeyboardButton("Минное Поле", callback_data="minefield")]]
        await query.edit_message_text("Мини-Игры:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif query.data == "minefield":
        now = datetime.now()
        if user["mines_played"] >= 3 and (now - user["last_mines"]) < timedelta(hours=24):
            await query.edit_message_text("Вы уже сыграли 3 раза за 24 часа. Подождите!")
            return
        reward = random.randint(10, 1000)
        user["coins"] += reward
        user["mines_played"] += 1
        user["last_mines"] = now
        await query.edit_message_text(f"Вы прошли Минное Поле и получили {reward} монет!")

    # ------------------- PvP -------------------
    elif query.data == "pvp":
        await query.edit_message_text("PvP пока упрощён: сражение между двумя игроками можно реализовать через команду /challenge")

# ------------------- Message handler -------------------
async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.chat.type == "private" or update.message.chat.type == "group":
        # Здесь можно добавить авто-события, таймеры для групп и ЛС
        pass

# ------------------- Команды -------------------
async def challenge(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    user_id = update.effective_user.id
    if len(args) != 1:
        await update.message.reply_text("Используйте: /challenge <user_id>")
        return
    target_id = int(args[0])
    if target_id not in users:
        await update.message.reply_text("Игрок не найден.")
        return
    user = users[user_id]
    target = users[target_id]
    dmg_user = random.randint(5, 15)
    dmg_target = random.randint(5, 15)
    result = f"PvP бой!\n{user['name']} наносит {dmg_user} урона\n{target['name']} наносит {dmg_target} урона\n"
    if dmg_user > dmg_target:
        user["xp"] += 10
        user["coins"] += 20
        result += f"{user['name']} победил и получил 10 XP и 20 монет!"
    elif dmg_user < dmg_target:
        target["xp"] += 10
        target["coins"] += 20
        result += f"{target['name']} победил и получил 10 XP и 20 монет!"
    else:
        result += "Ничья!"
    await update.message.reply_text(result)

# ------------------- Запуск -------------------
app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("profile", profile))
app.add_handler(CommandHandler("menu", menu))
app.add_handler(CommandHandler("challenge", challenge))
app.add_handler(CallbackQueryHandler(callback_handler))
app.add_handler(MessageHandler(filters.ALL, message_handler))

print("RPG бот с мини-играми запущен...")
app.run_polling()
