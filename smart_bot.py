# Этот проект живёт на GitHub
import asyncio
import logging
import logging.config # Добавляем импорт для конфигурации логирования
import random
import regex  # Библиотека для точного определения эмодзи (поддерживает все юникод-группы)
from datetime import datetime
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart, Command
from dotenv import load_dotenv
import os
import httpx

load_dotenv()  # Загружаем переменные окружения из .env
API_TOKEN = os.getenv("TG_TOKEN")
VOIDAI_API_KEY = os.getenv("VOIDAI_API_KEY")
RESPONSE_DELAY = int(os.getenv("RESPONSE_DELAY", 5)) # По умолчанию 5 секунд

# --- Настройки ---

# --- Конфигурация логирования ---
LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S"
        },
    },
    "handlers": {
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "level": "INFO",
            "formatter": "standard",
            "filename": "bot.log",
            "maxBytes": 10485760, # 10 MB
            "backupCount": 5,
            "encoding": "utf8"
        },
        "console": {
            "class": "logging.StreamHandler",
            "level": "INFO",
            "formatter": "standard"
        },
    },
    "loggers": {
        "": { # root logger
            "handlers": ["file", "console"],
            "level": "INFO",
            "propagate": True
        },
        "httpx": { # Отключаем подробные логи httpx
            "handlers": ["file", "console"],
            "level": "WARNING",
            "propagate": False
        },
    }
}

logging.config.dictConfig(LOGGING_CONFIG)
logger = logging.getLogger(__name__)

# --- Инициализация бота и диспетчера ---
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# Словарь для хранения состояния активных чатов
active_chats = {}

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


# --- Функция для получения ответа от VoidAI ---
async def get_voidai_response(message_history: list) -> str:
    url = "https://api.voidai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {VOIDAI_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "gemini-2.5-flash",
        "messages": message_history
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=payload, headers=headers)
        response.raise_for_status()  # Вызовет исключение для кодов 4xx/5xx
        data = response.json()
        return data["choices"][0]["message"]["content"]


# --- Функция для проверки доступности VoidAI API ---
async def check_voidai_api():
    logger.info("Проверка доступности VoidAI API...")
    url = "https://api.voidai.com/v1/models" # Эндпоинт для получения списка моделей
    headers = {
        "Authorization": f"Bearer {VOIDAI_API_KEY}"
    }
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            logger.info("VoidAI API доступен. Ключ API действителен.")
            return True
    except httpx.HTTPStatusError as e:
        logger.error(f"Ошибка HTTP при проверке VoidAI API: {e.response.status_code} - {e.response.text}")
        return False
    except httpx.RequestError as e:
        logger.error(f"Ошибка сети при проверке VoidAI API: {e}")
        return False
    except Exception as e:
        logger.error(f"Неизвестная ошибка при проверке VoidAI API: {e}")
        return False


# --- Функция для генерации и отправки ответа ---
async def generate_response(chat_id: int):
    logger.info(f"Запущена генерация ответа для чата {chat_id}")
    state = active_chats.get(chat_id)
    logger.debug(f"Состояние чата {chat_id} перед генерацией ответа: {state}")

    if not state:
        logger.warning(f"Чат {chat_id} не активен во время генерации ответа. Прекращаем выполнение.")
        return

    if state["is_waiting_for_user"]:
        logger.info(f"Бот ожидает ответа пользователя в чате {chat_id}. Прекращаем выполнение.")
        return

    try:
        await bot.send_chat_action(chat_id, "typing")
        logger.debug(f"Отправлен индикатор 'typing' в чат {chat_id}")

        # Отправляем историю сообщений в VoidAI API
        generated_text = await get_voidai_response(state["message_history"])
        logger.info(f"Получен ответ от Gemini для чата {chat_id}: {generated_text}")

        await bot.send_message(chat_id, generated_text)
        logger.info(f"Отправлен ответ в чат {chat_id}")

        state["is_waiting_for_user"] = True
        state["message_history"].clear()
        logger.info(f"Установлен флаг is_waiting_for_user и очищена история сообщений для чата {chat_id}")

    except Exception as e:
        logger.error(f"Ошибка при генерации или отправке ответа в чате {chat_id}: {e}")
        await bot.send_message(chat_id, "🤖 Извините, произошла ошибка при генерации ответа.")


# --- Обработчик команды /start ---
@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    logger.info(f"Получена команда /start от пользователя {message.from_user.id} в чате {message.chat.id}")
    await message.answer("👋 Привет! Я умный бот. Напиши мне что-нибудь — и я отвечу! О чём поговорим?")

# --- Команда /startconv ---
@dp.message(Command("startconv"))
async def start_conversation(message: types.Message):
    chat_id = message.chat.id
    logger.info(f"Получена команда /startconv от пользователя {message.from_user.id} в чате {chat_id}")

    if chat_id in active_chats:
        await message.answer("🤖 Режим разговора уже активирован в этом чате.")
        logger.info(f"Режим разговора уже активен в чате {chat_id}")
        return

    active_chats[chat_id] = {
        "message_history": [],
        "timer": None,
        "is_waiting_for_user": False
    }
    logger.debug(f"Инициализировано состояние чата {chat_id}: {active_chats[chat_id]}")
    await message.answer("🤖 Режим разговора активирован. Я присоединюсь к беседе, если будет пауза.")
    logger.info(f"Режим разговора активирован в чате {chat_id}")

# --- Команда /stopconv ---
@dp.message(Command("stopconv"))
async def stop_conversation(message: types.Message):
    chat_id = message.chat.id
    logger.info(f"Получена команда /stopconv от пользователя {message.from_user.id} в чате {chat_id}")

    if chat_id not in active_chats:
        await message.answer("🤖 Режим разговора не активирован в этом чате.")
        logger.info(f"Режим разговора не активен в чате {chat_id}")
        return

    state = active_chats[chat_id]
    if state["timer"]:
        state["timer"].cancel()
        logger.info(f"Таймер отменён для чата {chat_id}")

    del active_chats[chat_id]
    logger.debug(f"Состояние чата {chat_id} удалено.")
    await message.answer("🤖 Режим разговора отключён.")
    logger.info(f"Режим разговора отключён в чате {chat_id}")

# --- Обработчик любых сообщений ---
@dp.message()
async def handle_message(message: types.Message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    user_text = message.text

    logger.info(f"Получено сообщение от {user_id} в чате {chat_id}: {user_text}")

    if chat_id not in active_chats:
        logger.debug(f"Чат {chat_id} не активен, игнорируем сообщение.")
        return

    state = active_chats[chat_id]
    logger.debug(f"Текущее состояние чата {chat_id}: {state}")

    if state["is_waiting_for_user"]:
        state["is_waiting_for_user"] = False
        logger.info(f"Сброшен флаг is_waiting_for_user для чата {chat_id}")

    if user_text:
        if is_only_emoji(user_text):
            response_text = random.choice(EMOJI_RESPONSES)
            await message.answer(response_text)
            logger.info(f"Отправлен ответ на эмодзи в чат {chat_id}: {response_text}")
            return # Прекращаем дальнейшую обработку, если это только эмодзи
        
        state["message_history"].append({"role": "user", "content": user_text})
        logger.debug(f"Сообщение добавлено в историю чата {chat_id}. История: {state['message_history']}")

    if state["timer"]:
        state["timer"].cancel()
        logger.debug(f"Предыдущий таймер отменён для чата {chat_id}")

    state["timer"] = asyncio.get_event_loop().call_later(
        RESPONSE_DELAY,
        lambda: asyncio.create_task(generate_response(chat_id))
    )
    logger.info(f"Новый таймер установлен на {RESPONSE_DELAY} секунд для чата {chat_id}")


# --- Основная функция ---
async def main():
    print("🤖 Бот запущен! Нажмите Ctrl+C для остановки.")
    if not await check_voidai_api():
        logger.error("VoidAI API недоступен или ключ API недействителен. Бот не будет запущен.")
        return
    # Убираем 'allowed_updates', так как types.ALL_TYPES не существует в aiogram 3
    await dp.start_polling(bot, close_bot_session=True)

# Основная функция
if __name__ == "__main__":
    asyncio.run(main())