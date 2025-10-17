import asyncio
import logging
import random
import regex  # Библиотека для точного определения эмодзи (поддерживает все юникод-группы)
from datetime import datetime
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from dotenv import load_dotenv
import os

load_dotenv()  # Загружаем переменные окружения из .env
API_TOKEN = os.getenv("TG_TOKEN")

# --- Настройки ---

# --- Логирование ---
logging.basicConfig(level=logging.INFO)

# --- Инициализация бота и диспетчера ---
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# --- Набор случайных фраз для ответа на эмодзи ---
EMOJI_RESPONSES = [
    "😀 Отличный смайлик! Ещё один отправишь?",
    "😎 Настроение супер!",
    "😉 Выбираешь хорошо!",
    "😂 Даже не знаю что сказать!",
    "🤖 Эмодзи приняты, капитан!",
    "Ты сегодня в ударе!",
    "Lol"
]

# --- Проверка, содержит ли строка только эмодзи ---
def is_only_emoji(text: str) -> bool:
    if not text:
        return False
    text = text.strip()
    emoji_pattern = regex.compile(r'^(?:[\p{Emoji}\p{Emoji_Presentation}\p{Emoji_Modifier}\p{Emoji_Modifier_Base}\p{Emoji_Component}]+)$', flags=regex.UNICODE)
    return bool(emoji_pattern.fullmatch(text))


# --- Обработчик команды /start ---
@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    await message.answer("👋 Привет! Я эхо-бот. Напиши мне что-нибудь — и я повторю!")


# --- Обработчик любых сообщений ---
@dp.message()
async def echo_message(message: types.Message):
    if not message.text:
        return  # Не обрабатывать сообщения без текста

    user_text = message.text.lower()

    # Имитация активности (бот показывает, что «печатает» 1 секунду)
    await bot.send_chat_action(message.chat.id, "typing")
    await asyncio.sleep(1)

    # Если сообщение состоит только из эмодзи — отвечаем случайной фразой
    if is_only_emoji(message.text):
        response = random.choice(EMOJI_RESPONSES)
        await message.answer(response)
        return

    # Если в сообщении есть слова "время" или "времени", показываем дату и время
    if "время" in user_text or "времени" in user_text:
        current_time = datetime.now().strftime('%d.%m.%Y %H:%M:%S')
        response = f"🕒 Текущее время: {current_time}"
        await message.answer(response)
    else:
        await message.answer(message.text)


# --- Основная функция ---
async def main():
    print("🤖 Бот запущен! Нажмите Ctrl+C для остановки.")
    # Убираем 'allowed_updates', так как types.ALL_TYPES не существует в aiogram 3
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())