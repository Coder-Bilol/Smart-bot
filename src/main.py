# This project lives on GitHub
import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart, Command
from src.config import API_TOKEN
from src.api_client import check_voidai_api
from src.logging_config import logger
from src.bot_handlers import cmd_start, start_conversation, stop_conversation, handle_message, set_bot_instance
from src.chat_state_manager import active_chats

# --- Bot and Dispatcher Initialization ---
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# Set the bot instance in the bot_handlers module to avoid circular imports
set_bot_instance(bot)

# --- Register handlers ---
dp.message(CommandStart())(cmd_start)
dp.message(Command("startconv"))(start_conversation)
dp.message(Command("stopconv"))(stop_conversation)
dp.message()(handle_message)

# --- Main function ---
async def main():
    print("Bot launched! Press Ctrl+C to stop.")
    if not await check_voidai_api():
        logger.error("VoidAI API is unavailable or API key is invalid. Bot will not be launched.")
        return
    # Remove 'allowed_updates' as types.ALL_TYPES does not exist in aiogram 3
    await dp.start_polling(bot, close_bot_session=True)

# Main function
if __name__ == "__main__":
    asyncio.run(main())