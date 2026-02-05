from telegram import Update, InputMediaPhoto, InputFile
from telegram.ext import Updater, CommandHandler, CallbackContext
import random
from PIL import Image, ImageDraw, ImageFont
import requests
from io import BytesIO

# ---------- Настройки ----------
ADMIN_ID = 7652697216  # Ваш Telegram ID
TOKEN = "8349946765:AAG31kDyeywXsYk1z3GZMJ19J8BkkxpgVvQ"

# ---------- Данные ----------
cards = []  # Список всех карточек
user_collections = {}  # Коллекции пользователей
rarity_probabilities = {
    "обычная": 60,
    "редкая": 30,
    "эпическая": 9,
    "легендарная": 1
}

rarity_emojis = {
    "обычная": "⚪",
    "редкая": "🔵",
    "эпическая": "🟣",
    "легендарная": "🟡"
}

# ---------- Функции ----------
def add_card(name, description, rarity, image_url, admin_id):
    if admin_id != ADMIN_ID:
        return "У вас нет прав админа."
    if rarity not in rarity_probabilities:
        return f"Редкость {rarity} не существует."
    if any(card["name"] == name for card in cards):
        return "Карточка с таким именем уже существует."
    cards.append({
        "name": name,
        "description": description,
        "rarity": rarity,
        "image": image_url
    })
    return f"Карточка '{name}' ({rarity}) успешно добавлена."

def change_rarity(name, new_rarity, admin_id):
    if admin_id != ADMIN_ID:
        return "У вас нет прав админа."
    if new_rarity not in rarity_probabilities:
        return f"Редкость {new_rarity} не существует."
    for card in cards:
        if card["name"] == name:
            card["rarity"] = new_rarity
            return f"Редкость карточки '{name}' изменена на {new_rarity}."
    return f"Карточка '{name}' не найдена."

def collect_card(user_id):
    if not cards:
        return None
    weights = [rarity_probabilities[card["rarity"]] for card in cards]
    card = random.choices(cards, weights=weights, k=1)[0]
    if user_id not in user_collections:
        user_collections[user_id] = []
    user_collections[user_id].append(card)
    return card

def event_collect_card(user_id):
    # Ивентовый сбор: шанс легендарной увеличен в 5 раз
    if not cards:
        return None
    adjusted_probabilities = {}
    for r, p in rarity_probabilities.items():
        adjusted_probabilities[r] = p * 5 if r == "легендарная" else p
    weights = [adjusted_probabilities[card["rarity"]] for card in cards]
    card = random.choices(cards, weights=weights, k=1)[0]
    if user_id not in user_collections:
        user_collections[user_id] = []
    user_collections[user_id].append(card)
    return card

# ---------- Визуальная генерация коллекции ----------
def generate_collection_image(user_id):
    collection = user_collections.get(user_id, [])
    if not collection:
        return None
    
    # Группируем по редкости
    grouped = {}
    for card in collection:
        grouped.setdefault(card["rarity"], []).append(card)
    
    # Настройки изображения
    card_size = (100, 100)
    padding = 20
    font = ImageFont.load_default()
    rarities_order = ["легендарная", "эпическая", "редкая", "обычная"]
    
    # Размеры итогового изображения
    max_cards_in_row = max(len(grouped.get(r, [])) for r in rarities_order) or 1
    width = max_cards_in_row * (card_size[0] + padding) + padding
    height = sum(len(grouped.get(r, [])) * (card_size[1] + padding) for r in rarities_order) + len(rarities_order) * padding
    
    img = Image.new("RGB", (width, height), color=(30,30,30))
    draw = ImageDraw.Draw(img)
    
    y_offset = padding
    for rarity in rarities_order:
        cards_in_rarity = grouped.get(rarity, [])
        if not cards_in_rarity:
            continue
        x_offset = padding
        for card in cards_in_rarity:
            try:
                response = requests.get(card["image"])
                card_img = Image.open(BytesIO(response.content)).resize(card_size)
                img.paste(card_img, (x_offset, y_offset))
                draw.text((x_offset, y_offset + card_size[1]), f"{rarity_emojis[rarity]} {card['name']}", font=font, fill=(255,255,255))
                x_offset += card_size[0] + padding
            except:
                continue
        y_offset += card_size[1] + padding + 15
    
    output = BytesIO()
    img.save(output, format="PNG")
    output.seek(0)
    return output

# ---------- Команды ----------
def collect(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    card = collect_card(user_id)
    if not card:
        update.message.reply_text("Пока нет карточек для сбора.")
        return
    update.message.reply_photo(
        photo=card["image"],
        caption=f"Вы получили карточку: {card['name']} ({card['rarity']})\n{card['description']}"
    )

def event_collect(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    card = event_collect_card(user_id)
    if not card:
        update.message.reply_text("Пока нет карточек для сбора.")
        return
    update.message.reply_photo(
        photo=card["image"],
        caption=f"🎉 Ивент! Вы получили карточку: {card['name']} ({card['rarity']})\n{card['description']}"
    )

def mycards(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    collection = user_collections.get(user_id, [])
    if not collection:
        update.message.reply_text("У вас пока нет карточек.")
        return
    grouped = {}
    for card in collection:
        grouped.setdefault(card["rarity"], []).append(card)
    message = "🎴 Ваша коллекция:\n\n"
    for rarity in ["легендарная", "эпическая", "редкая", "обычная"]:
        if rarity in grouped:
            message += f"{rarity_emojis[rarity]} {rarity.capitalize()} ({len(grouped[rarity])}):\n"
            for card in grouped[rarity]:
                message += f" - {card['name']}\n"
            message += "\n"
    update.message.reply_text(message)

def add(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    try:
        args = " ".join(context.args).split(";")
        if len(args) != 4:
            update.message.reply_text("Использование: /add имя;редкость;описание;ссылка_на_картинку")
            return
        name, rarity, description, image = args
        result = add_card(name.strip(), description.strip(), rarity.strip(), image.strip(), user_id)
        update.message.reply_text(result)
    except Exception as e:
        update.message.reply_text(f"Ошибка: {e}")

def changerarity(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    try:
        args = " ".join(context.args).split(";")
        if len(args) != 2:
            update.message.reply_text("Использование: /changerarity имя;новая_редкость")
            return
        name, new_rarity = args
        result = change_rarity(name.strip(), new_rarity.strip(), user_id)
        update.message.reply_text(result)
    except Exception as e:
        update.message.reply_text(f"Ошибка: {e}")

def showcollection(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    img = generate_collection_image(user_id)
    if not img:
        update.message.reply_text("У вас пока нет карточек.")
        return
    update.message.reply_photo(photo=InputFile(img), caption="🎴 Ваша коллекция")

# ---------- Запуск бота ----------
updater = Updater(TOKEN)
dispatcher = updater.dispatcher

dispatcher.add_handler(CommandHandler("collect", collect))
dispatcher.add_handler(CommandHandler("event_collect", event_collect))
dispatcher.add_handler(CommandHandler("mycards", mycards))
dispatcher.add_handler(CommandHandler("add", add))
dispatcher.add_handler(CommandHandler("changerarity", changerarity))
dispatcher.add_handler(CommandHandler("showcollection", showcollection))

updater.start_polling()
updater.idle()
