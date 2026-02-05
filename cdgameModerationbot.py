import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command, CommandStart, ChatTypeFilter
from aiogram.enums import ChatType
from aiogram.types import ChatPermissions

TOKEN = "8349946765:AAG31kDyeywXsYk1z3GZMJ19J8BkkxpgVvQ"
LOG_CHANNEL_ID = -1001234567890  # лог-канал

bot = Bot(TOKEN)
dp = Dispatcher()

# ------------------ РАНГИ ------------------

RANKS = {
    1: "Стажёр",
    2: "Мл. Модератор",
    3: "Модератор",
    4: "Ст. Модератор",
    5: "Администратор",
    6: "Владелец"
}

COMMANDS_BY_RANK = {
    1: {"mute", "ban"},
    2: {"mute", "ban", "unban", "unwarn"},
    3: {"mute", "ban", "unban", "unwarn", "kick"},
    4: {"mute", "ban", "unban", "unwarn", "kick"},
    5: {"mute", "ban", "unban", "unwarn", "kick", "gban", "gmute"},
    6: {"*"}
}

# ------------------ ХРАНИЛИЩА ------------------

users_roles = {}        # chat_id -> {user_id: rank}
chat_to_network = {}   # chat_id -> network_id
networks = {}           # network_id -> [chat_ids]

# ------------------ HELPERS ------------------

async def get_rank(chat_id: int, user_id: int) -> int:
    member = await bot.get_chat_member(chat_id, user_id)
    if member.status == "creator":
        return 6
    return users_roles.get(chat_id, {}).get(user_id, 0)

def can_use(rank: int, command: str) -> bool:
    if rank == 6:
        return True
    return command in COMMANDS_BY_RANK.get(rank, set())

async def log_action(action, moderator, target, reason, chat, rank):
    text = (
        f"🧾 *Модерация*\n\n"
        f"👮 {moderator.full_name} (`{moderator.id}`)\n"
        f"🎖 Ранг: {RANKS.get(rank)}\n"
        f"👤 Нарушитель: {target.full_name} (`{target.id}`)\n"
        f"⚖️ Действие: *{action}*\n"
        f"📝 Причина: {reason}\n"
        f"💬 Чат: {chat.title} (`{chat.id}`)"
    )
    await bot.send_message(LOG_CHANNEL_ID, text, parse_mode="Markdown")

# ------------------ START (ЛС) ------------------

@dp.message(CommandStart(), ChatTypeFilter(ChatType.PRIVATE))
async def start_private(message: types.Message):
    await message.answer(
        "🛡 *Бот модерации*\n\n"
        "Я работаю *только в группах*.\n"
        "Добавь меня в чат и выдай права администратора.\n\n"
        "Все команды доступны только в группах.",
        parse_mode="Markdown"
    )

# ------------------ ВЫДАЧА РАНГОВ ------------------

@dp.message(Command("setrank"), ChatTypeFilter(ChatType.GROUP, ChatType.SUPERGROUP))
async def set_rank(message: types.Message):
    if not message.reply_to_message:
        return await message.reply("Ответь на пользователя")

    args = message.text.split()
    if len(args) < 2:
        return await message.reply("Пример: /setrank 3")

    new_rank = int(args[1])
    chat_id = message.chat.id

    issuer_rank = await get_rank(chat_id, message.from_user.id)
    if issuer_rank < 5:
        return await message.reply("⛔ Нет прав")

    users_roles.setdefault(chat_id, {})[
        message.reply_to_message.from_user.id
    ] = new_rank

    await message.reply(f"✅ Назначен ранг: {RANKS.get(new_rank)}")

# ------------------ MUTE ------------------

@dp.message(Command("mute"), ChatTypeFilter(ChatType.GROUP, ChatType.SUPERGROUP))
async def mute(message: types.Message):
    if not message.reply_to_message:
        return await message.reply("Ответь на пользователя")

    rank = await get_rank(message.chat.id, message.from_user.id)
    if not can_use(rank, "mute"):
        return await message.reply("⛔ Нет прав")

    reason = message.text.partition(" ")[2] or "Не указана"
    target = message.reply_to_message.from_user

    await bot.restrict_chat_member(
        message.chat.id,
        target.id,
        ChatPermissions(can_send_messages=False)
    )

    await message.reply(f"🔇 Мут\nПричина: {reason}")
    await log_action("MUTE", message.from_user, target, reason, message.chat, rank)

# ------------------ BAN ------------------

@dp.message(Command("ban"), ChatTypeFilter(ChatType.GROUP, ChatType.SUPERGROUP))
async def ban(message: types.Message):
    if not message.reply_to_message:
        return await message.reply("Ответь на пользователя")

    rank = await get_rank(message.chat.id, message.from_user.id)
    if not can_use(rank, "ban"):
        return await message.reply("⛔ Нет прав")

    reason = message.text.partition(" ")[2] or "Не указана"
    target = message.reply_to_message.from_user

    await bot.ban_chat_member(message.chat.id, target.id)
    await message.reply(f"⛔ Бан\nПричина: {reason}")

    await log_action("BAN", message.from_user, target, reason, message.chat, rank)

# ------------------ UNBAN ------------------

@dp.message(Command("unban"), ChatTypeFilter(ChatType.GROUP, ChatType.SUPERGROUP))
async def unban(message: types.Message):
    rank = await get_rank(message.chat.id, message.from_user.id)
    if not can_use(rank, "unban"):
        return await message.reply("⛔ Нет прав")

    args = message.text.split()
    if len(args) < 2:
        return await message.reply("Пример: /unban user_id")

    user_id = int(args[1])
    await bot.unban_chat_member(message.chat.id, user_id)
    await message.reply("✅ Пользователь разбанен")

# ------------------ KICK ------------------

@dp.message(Command("kick"), ChatTypeFilter(ChatType.GROUP, ChatType.SUPERGROUP))
async def kick(message: types.Message):
    if not message.reply_to_message:
        return await message.reply("Ответь на пользователя")

    rank = await get_rank(message.chat.id, message.from_user.id)
    if not can_use(rank, "kick"):
        return await message.reply("⛔ Нет прав")

    target = message.reply_to_message.from_user
    await bot.ban_chat_member(message.chat.id, target.id)
    await bot.unban_chat_member(message.chat.id, target.id)

    await message.reply("👢 Пользователь кикнут")

# ------------------ GBAN ------------------

@dp.message(Command("gban"), ChatTypeFilter(ChatType.GROUP, ChatType.SUPERGROUP))
async def gban(message: types.Message):
    if not message.reply_to_message:
        return await message.reply("Ответь на пользователя")

    rank = await get_rank(message.chat.id, message.from_user.id)
    if not can_use(rank, "gban"):
        return await message.reply("⛔ Нет прав")

    chat_id = message.chat.id
    if chat_id not in chat_to_network:
        return await message.reply("❌ Чат не в сетке")

    reason = message.text.partition(" ")[2] or "Не указана"
    target = message.reply_to_message.from_user

    net_id = chat_to_network[chat_id]
    for cid in networks.get(net_id, []):
        try:
            await bot.ban_chat_member(cid, target.id)
        except:
            pass

    await message.reply(f"🌐 Глобальный бан\nПричина: {reason}")

# ------------------ RUN ------------------

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
