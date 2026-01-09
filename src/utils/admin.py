from aiogram import types

async def is_admin(message: types.Message):
    chat_member = await message.bot.get_chat_member(message.chat.id, message.from_user.id)
    return chat_member.status in ["administrator", "creator"]
