import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import random
import time

TOKEN = "8349946765:AAG31kDyeywXsYk1z3GZMJ19J8BkkxpgVvQ"
bot = telebot.TeleBot(TOKEN)

# Пользовательские профили
users = {}

# Настройки напитков
drinks = ["Вино", "Пиво", "Чай", "Кофе", "Водка"]

# Магазин
shop_items = {
    "bonus_20": {"name": "+20% к бонусным литрам", "cost": 150},
    "double_drink": {"name": "Выпить дважды", "cost": 300}
}

# Вспомогательные функции
def get_user(user_id):
    if user_id not in users:
        users[user_id] = {
            "liters": 0,
            "last_drink": 0,
            "bonus": False,
            "double_drink": False
        }
    return users[user_id]

def random_cooldown():
    return random.randint(3600, 18000)  # 1-5 часов в секундах

# Команда /start
@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id,
                     "Привет! 🍹 Я бот для питья напитков. Нажми /drink чтобы выпить или /shop чтобы открыть магазин.")

# Команда /drink
@bot.message_handler(commands=['drink'])
def drink(message):
    user = get_user(message.from_user.id)
    now = time.time()
    
    # Проверка кулдауна
    if now - user["last_drink"] < random_cooldown():
        remaining = int((random_cooldown() - (now - user["last_drink"])) / 60)
        bot.send_message(message.chat.id, f"⏳ Подожди {remaining} минут прежде чем пить снова!")
        return
    
    # Кнопки выбора напитка
    markup = InlineKeyboardMarkup()
    for d in drinks:
        markup.add(InlineKeyboardButton(d, callback_data=f"drink_{d}"))
    bot.send_message(message.chat.id, "Выбери напиток:", reply_markup=markup)

# Обработка нажатия кнопок
@bot.callback_query_handler(func=lambda call: call.data.startswith("drink_"))
def callback_drink(call):
    drink_name = call.data.split("_")[1]
    user = get_user(call.from_user.id)
    
    # Кол-во литров за напиток
    liters = random.randint(1, 3)
    
    # Бонус
    bonus_liters = 0
    if user["bonus"]:
        if random.random() < 0.2:
            bonus_liters = random.randint(1, 2)
    
    total_liters = liters + bonus_liters
    user["liters"] += total_liters
    user["last_drink"] = time.time()
    
    bot.answer_callback_query(call.id)
    bot.send_message(call.message.chat.id,
                     f"Ты выпил {drink_name} и получил {total_liters} литров 🍹 (бонус: {bonus_liters})\nВсего литров: {user['liters']}")
    
    # Проверка на двойное питьё
    if user["double_drink"]:
        user["double_drink"] = False
        bot.send_message(call.message.chat.id, "🎉 У тебя есть возможность выпить снова!")
        drink(call.message)

# Команда /shop
@bot.message_handler(commands=['shop'])
def shop(message):
    markup = InlineKeyboardMarkup()
    for key, item in shop_items.items():
        markup.add(InlineKeyboardButton(f"{item['name']} ({item['cost']} литров)", callback_data=f"shop_{key}"))
    bot.send_message(message.chat.id, "Магазин:", reply_markup=markup)

# Покупка из магазина
@bot.callback_query_handler(func=lambda call: call.data.startswith("shop_"))
def buy_item(call):
    item_key = call.data.split("_")[1]
    user = get_user(call.from_user.id)
    item = shop_items[item_key]
    
    if user["liters"] < item["cost"]:
        bot.answer_callback_query(call.id, "❌ Недостаточно литров")
        return
    
    user["liters"] -= item["cost"]
    
    if item_key == "bonus_20":
        user["bonus"] = True
    elif item_key == "double_drink":
        user["double_drink"] = True
    
    bot.answer_callback_query(call.id, f"✅ Куплено: {item['name']}!\nОсталось литров: {user['liters']}")

# Команда /profile
@bot.message_handler(commands=['profile'])
def profile(message):
    user = get_user(message.from_user.id)
    text = f"👤 Профиль:\nЛитров: {user['liters']}\nБонус: {'Да' if user['bonus'] else 'Нет'}\nДвойное питьё: {'Да' if user['double_drink'] else 'Нет'}"
    bot.send_message(message.chat.id, text)

# Запуск бота
bot.polling()
