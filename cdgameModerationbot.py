import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import ChatPermissions

TOKEN = "8349946765:AAG31kDyeywXsYk1z3GZMJ19J8BkkxpgVvQ"
bot = Bot(TOKEN)
dp = Dispatcher()

# Ранги
RANKS = {
    1: "Стажёр",
    2: "Мл. Модератор",
    3: "Модератор",
    4: "Ст. Модератор",
    5: "Администратор"
}

# какие команды доступны
COMMANDS_BY_RANK = {
    1: {"mute", "ban"},
    2: {"mute", "ban", "unwarn", "unban"},
    3: {"mute", "ban", "unwarn", "unban", "kick"},
    4: {"mute", "ban", "unwarn", "unban", "kick"},
    5: {"mute", "ban", "unwarn", "unban", "kick", "gban", "gmute"},
}

users_roles = {}          # chat_id -> {user_id: rank}
chat_to_network = {}     # chat_id -> network_id
networks = {}             # network_id -> [chat_ids]

# -------- helpers --------

async def get_rank(chat_id, user_id):
    member = await bot.get_chat_member(chat_id, user_id)
    if member.status == "creator":
        return 6
    return users_roles.get(chat_id, {}).get(user_id, 0)

def can_use(rank, command):
    if rank == 6:
        return True
    return command in COMMANDS_BY_RANK.get(rank, set())

# -------- выдача прав --------

@dp.message(Command("setrank"))
async def set_rank(message: types.Message):
    if not message.reply_to_message:
        return await message.reply("Ответь на пользователя")

    rank = int(message.text.split()[1])
    chat_id = message.chat.id

    issuer_rank = await get_rank(chat_id, message.from_user.id)
    if issuer_rank < 5:
        return await message.reply("⛔ Нет прав")

    users_roles.setdefault(chat_id, {})[
        message.reply_to_message.from_user.id
    ] = rank

    await message.reply(
        f"✅ Назначен ранг: {RANKS.get(rank)}"
    )

# -------- наказания --------

@dp.message(Command("mute"))
async def mute(message: types.Message):
    if not message.reply_to_message:
        return await message.reply("Ответь на пользователя")

    reason = message.text.partition(" ")[2] or "Не указана"
    rank = await get_rank(message.chat.id, message.from_user.id)

    if not can_use(rank, "mute"):
        return await message.reply("⛔ Нет прав")

    await bot.restrict_chat_member(
        message.chat.id,
        message.reply_to_message.from_user.id,
        ChatPermissions(can_send_messages=False)
    )

    await message.reply(f"🔇 Мут\nПричина: {reason}")

# -------- глобальные наказания --------

@dp.message(Command("gban"))
async def gban(message: types.Message):
    chat_id = message.chat.id
    rank = await get_rank(chat_id, message.from_user.id)

    if not can_use(rank, "gban"):
        return await message.reply("⛔ Нет прав")

    if chat_id not in chat_to_network:
        return await message.reply("❌ Чат не привязан к сетке")

    network_id = chat_to_network[chat_id]
    reason = message.text.partition(" ")[2] or "Не указана"

    for cid in networks.get(network_id, []):
        try:
            await bot.ban_chat_member(
                cid,
                message.reply_to_message.from_user.id
            )
        except:
            pass

    await message.reply(f"🌐 Глобальный бан\nПричина: {reason}")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

