import asyncio
import random
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler, MessageHandler, filters

# ------------------- Конфиг -------------------
TOKEN = "8349946765:AAG31kDyeywXsYk1z3GZMJ19J8BkkxpgVvQ"
ADMIN_IDS = [7652697216]

# ------------------- Хранилище (вместо базы данных) -------------------
groups = {}  # group_id -> {"last_card_time": datetime, "current_card": None, "card_spawn_time": None}
users = {}   # user_id -> {"coins": 0, "points": 0, "cards": set()}
cards = {}   # card_id -> {"name": str, "rarity": str, "drop_chance": int, "image_ids": list, "price": int}
market = {}  # card_id -> {"user_id": int, "price": int}
claims = {}  # group_id -> {"active_card_id": card_id, "spawn_time": datetime}

# ------------------- Вспомогательные функции -------------------
def rarity_emoji(rarity):
    return {"Common":"⚪", "Rare":"🔵", "Epic":"🟣", "Legendary":"🟡"}.get(rarity, "⚪")

def users_with_card(card_id):
    total_users = len(users)
    count = sum(1 for u in users.values() if card_id in u["cards"])
    percent = (count/total_users*100) if total_users > 0 else 0
    return count, percent

# ------------------- Команды -------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет! Используй /menu чтобы открыть главное меню.")

async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Мини-Игры", callback_data="mini_games")],
        [InlineKeyboardButton("Мой Гарем", callback_data="harem")]
    ]
    await update.message.reply_text("Меню:", reply_markup=InlineKeyboardMarkup(keyboard))

async def harem_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    if user_id not in users or not users[user_id]["cards"]:
        await query.edit_message_text("У вас пока нет карточек.")
        return
    # Показываем первую карточку
    card_id = next(iter(users[user_id]["cards"]))
    await show_card(query, card_id, user_id, 0)

async def show_card(query, card_id, user_id, photo_index):
    card = cards[card_id]
    have_card = "✅" if card_id in users[user_id]["cards"] else "❌"
    count, percent = users_with_card(card_id)
    text = f"🆔 {card_id}\n👤 Имя: {card['name']}\n💎 Редкость: {rarity_emoji(card['rarity'])} {card['rarity']}\n💍 Есть у вас: {have_card}\n🌎 Есть у {count} ({percent:.2f}%) пользователей"
    keyboard = [
        [InlineKeyboardButton("📷 Следующее фото", callback_data=f"photo:{card_id}:{(photo_index+1)%len(card['image_ids'])}")],
        [InlineKeyboardButton("⭐ В избранное", callback_data=f"fav:{card_id}")]
    ]
    await query.edit_message_media(media=InputMediaPhoto(card['image_ids'][photo_index], caption=text), reply_markup=InlineKeyboardMarkup(keyboard))

async def photo_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    _, card_id, photo_index = query.data.split(":")
    card_id = int(card_id)
    photo_index = int(photo_index)
    user_id = query.from_user.id
    await show_card(query, card_id, user_id, photo_index)

# ------------------- Таймер и карточки -------------------
async def check_card_spawn(group_id, chat):
    if group_id not in groups:
        groups[group_id] = {"last_card_time": datetime.now() - timedelta(hours=5)}
    group = groups[group_id]
    now = datetime.now()
    if group.get("current_card") is None and (now - group["last_card_time"]) >= timedelta(hours=5):
        # Выбираем карточку случайно по шансам
        card_list = list(cards.values())
        card = random.choice(card_list)
        group["current_card"] = card
        group["card_spawn_time"] = now
        claims[group_id] = {"active_card_id": card, "spawn_time": now, "claimed": False}
        keyboard = [[InlineKeyboardButton("Забрать", callback_data=f"claim:{id(card)}")]]
        await chat.send_photo(card['image_ids'][0], caption=f"О, что это тут? Вайфу заблудилась!", reply_markup=InlineKeyboardMarkup(keyboard))
        # Таймер исчезновения через 20 минут
        asyncio.create_task(card_timeout(group_id, chat, 20*60))

async def card_timeout(group_id, chat, timeout):
    await asyncio.sleep(timeout)
    claim = claims.get(group_id)
    if claim and not claim.get("claimed", False):
        await chat.send_message("Тут была вайфу, но она убежала!")
        groups[group_id]["last_card_time"] = datetime.now()
        groups[group_id]["current_card"] = None
        claims.pop(group_id, None)

async def claim_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    group_id = query.message.chat_id
    user_id = query.from_user.id
    claim = claims.get(group_id)
    if not claim or claim.get("claimed", False):
        await query.edit_message_caption("Здесь была вайфу, но ее кто-то украл...")
        return
    # Забирать карточку
    card = claim["active_card_id"]
    users.setdefault(user_id, {"coins":0,"points":0,"cards":set()})
    users[user_id]["cards"].add(id(card))
    claim["claimed"] = True
    await query.edit_message_caption(f"@{query.from_user.username}, вы забрали {rarity_emoji(card['rarity'])} {card['name']}! Вайфу пополнила ваш Гарем!")
    groups[group_id]["last_card_time"] = datetime.now()
    groups[group_id]["current_card"] = None
    claims.pop(group_id, None)

# ------------------- Message handler для групп -------------------
async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.chat.type == "private":
        keyboard = [[InlineKeyboardButton("Добавить в чат", url="https://t.me/ВАШ_Бот?startgroup=true")]]
        await update.message.reply_text("Я работаю только в группах", reply_markup=InlineKeyboardMarkup(keyboard))
        return
    group_id = update.message.chat_id
    await check_card_spawn(group_id, update.message.chat)

# ------------------- Основной запуск -------------------
app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("menu", menu))
app.add_handler(MessageHandler(filters.ALL, message_handler))
app.add_handler(CallbackQueryHandler(photo_callback, pattern="^photo:"))
app.add_handler(CallbackQueryHandler(claim_callback, pattern="^claim:"))

print("Бот запущен...")
app.run_polling()
