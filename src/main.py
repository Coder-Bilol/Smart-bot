# This project lives on GitHub
import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart, Command
from config import API_TOKEN
from api_client import check_voidai_api
from logging_config import logger
from bot_handlers import cmd_start, cmd_role, cmd_goal, cmd_timeout, cmd_statusconv, start_conversation, stop_conversation, handle_message
from chat_state_manager import active_chats, db

# --- Bot and Dispatcher Initialization ---
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# --- Register handlers ---
dp.message(CommandStart())(cmd_start)
dp.message(Command("role"))(cmd_role)
dp.message(Command("goal"))(cmd_goal)
dp.message(Command("timeout"))(cmd_timeout)
dp.message(Command("statusconv"))(cmd_statusconv)
dp.message(Command("startconv"))(start_conversation)
dp.message(Command("stopconv"))(stop_conversation)
dp.message()(handle_message)

# --- Main function ---
async def main():
    print("Bot launched! Press Ctrl+C to stop.")
    
    # Initialize Database
    db.init_db()
    
    if not await check_voidai_api():
        logger.error("VoidAI API is unavailable or API key is invalid. Bot will not be launched.")
        return
    # Remove 'allowed_updates' as types.ALL_TYPES does not exist in aiogram 3
    await dp.start_polling(bot, close_bot_session=True)

# Main function
if __name__ == "__main__":
    asyncio.run(main())