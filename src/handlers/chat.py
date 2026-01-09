import asyncio
from aiogram import Router, types, Bot
from aiogram.filters import CommandStart, Command

from config import RESPONSE_DELAY, MAX_HISTORY_MESSAGES
from logging_config import logger
from chat_state_manager import active_chats, db
from api_client import get_llm_response
from utils.prompts import read_prompt_file
from emoji_utils import is_only_emoji
from responses import get_emoji_response
from moderator import Moderator

router = Router()
moderator = Moderator()

def ensure_transient_state(chat_id):
    if chat_id not in active_chats:
        active_chats[chat_id] = {
            "timer": None,
            "is_waiting_for_user": False,
            "reply_to_message_id": None
        }

@router.message(CommandStart())
async def cmd_start(message: types.Message):
    logger.info(f"Received /start command from user {message.from_user.id} in chat {message.chat.id}")
    await message.answer("👋 Привет! Я умный бот. Напиши мне что-нибудь и я отвечу! О чём поговорим?")

@router.message(Command("help"))
async def cmd_help(message: types.Message):
    help_text = """
🤖 **Smart Bot — Справка**

Я — умный бот с ИИ, который может поддерживать беседу и модерировать чат.

**📝 Основные команды:**
• `/start` — Приветствие
• `/help` — Эта справка
• `/graylist` — Показать список нарушителей чата

**💬 Режим разговора (админы):**
• `/startconv` — Включить режим общения
• `/stopconv` — Выключить режим общения
• `/statusconv` — Показать настройки

**⚙️ Настройки (админы):**
• `/role [текст]` — Задать роль бота
• `/goal [текст]` — Задать цель бота
• `/timeout [сек]` — Задержка ответа
• `/model` — Выбрать модель ИИ

**🛡 Модерация (админы):**
• `/groupabout [текст]` — Настроить тематику (контекст) чата
• `/mod_settings` — Настройки модерации
• `/strict [число]` — Порог нарушений
"""
    await message.answer(help_text, parse_mode="Markdown")

@router.message(Command("startconv"))
async def start_conversation(message: types.Message):
    chat_id = message.chat.id
    logger.info(f"Received /startconv command from user {message.from_user.id} in chat {chat_id}")

    if chat_id in active_chats:
        await message.answer("🤖 Conversation mode is already activated in this chat.")
        return

    ensure_transient_state(chat_id)
    
    # Persist state
    await db.update_chat_settings(chat_id, is_active=True)
    
    logger.debug(f"Chat state {chat_id} initialized.")
    await message.answer("🤖 Conversation mode activated. I will join the conversation if there is a pause.")
    logger.info(f"Conversation mode activated in chat {chat_id}")

@router.message(Command("stopconv"))
async def stop_conversation(message: types.Message):
    chat_id = message.chat.id
    logger.info(f"Received /stopconv command from user {message.from_user.id} in chat {chat_id}")

    if chat_id not in active_chats:
        await message.answer("🤖 Conversation mode is not activated in this chat.")
        return

    state = active_chats[chat_id]
    if state["timer"]:
        state["timer"].cancel()

    del active_chats[chat_id]
    
    # Persist state
    await db.update_chat_settings(chat_id, is_active=False)
    
    await message.answer("🤖 Conversation mode deactivated.")
    logger.info(f"Conversation mode deactivated in chat {chat_id}")

# --- Response Logic ---
async def generate_response(chat_id: int, bot: Bot):
    logger.info(f"Response generation started for chat {chat_id}")
    state = active_chats.get(chat_id)
    
    if not state:
        return

    if state["is_waiting_for_user"]:
        return

    try:
        await bot.send_chat_action(chat_id, "typing")

        base_role = read_prompt_file("role_prompt.md")
        base_goal = read_prompt_file("goal_prompt.md")
        
        settings = await db.get_chat_settings(chat_id)
        custom_role = settings.get("custom_role", "")
        custom_goal = settings.get("custom_goal", "")
        current_model = settings.get("model")

        system_prompt = f"# Role\n{base_role}\n{custom_role}\n\n# Goal\n{base_goal}\n{custom_goal}"
        
        history = await db.get_chat_history(chat_id, limit=MAX_HISTORY_MESSAGES)
        full_history = [{"role": "system", "content": system_prompt}] + history

        generated_text = await get_llm_response(full_history, model=current_model)
        
        await bot.send_message(chat_id, generated_text, reply_to_message_id=state.get("reply_to_message_id"))
        
        await db.add_message(chat_id, "assistant", generated_text)
        
        state["is_waiting_for_user"] = True

    except Exception as e:
        logger.error(f"Error generating response in chat {chat_id}: {e}")
        if bot:
            await bot.send_message(chat_id, "🤖 Sorry, an error occurred while generating the response.")
        if state:
            state["is_waiting_for_user"] = True

@router.message()
async def handle_message(message: types.Message):
    bot = message.bot
    chat_id = message.chat.id
    user_text = message.text

    if chat_id not in active_chats:
        return

    state = active_chats[chat_id]
    
    state["reply_to_message_id"] = None
    if message.reply_to_message and message.reply_to_message.from_user.id == bot.id:
        state["reply_to_message_id"] = message.message_id

    if state["is_waiting_for_user"]:
        state["is_waiting_for_user"] = False

    if user_text:
        if is_only_emoji(user_text):
            response_text = get_emoji_response()
            await message.answer(response_text)
            state["is_waiting_for_user"] = True
            return
        
        # --- Moderation Check ---
        settings = await db.get_chat_settings(chat_id)
        history = await db.get_chat_history(chat_id, limit=5)
        mod_result = await moderator.check_message(
            user_text, 
            history, 
            chat_context=settings.get("chat_context", "")
        )
        
        if mod_result.get("status") == "violation":
            user_id = message.from_user.id
            await db.add_violation(user_id, chat_id)
            violation_count = await db.get_violation_count(user_id, chat_id)
            
            strict_threshold = settings.get("strict_threshold", 2)
            
            if violation_count < strict_threshold:
                # Warning: not yet at threshold
                await message.reply(
                    f"⚠️ **Предупреждение!** Ваше сообщение нарушает правила чата ({mod_result.get('category')}).\n"
                    f"Причина: {mod_result.get('reason')}\n"
                    f"Нарушений: {violation_count}/{strict_threshold}. Ещё {strict_threshold - violation_count} и вы будете ограничены."
                )
                return  # Stop processing this message
            else:
                # At or above threshold: Restriction
                await message.reply(
                    f"🚫 **Ограничения применены.** Вы неоднократно нарушали правила чата.\n"
                    f"Категория: {mod_result.get('category')}\n"
                    "Вы замучены или забанены согласно настройкам чата."
                )
                
                try:
                    mod_action = settings.get("mod_action", "mute")
                    if mod_action == "ban":
                        await bot.ban_chat_member(chat_id=chat_id, user_id=user_id)
                    else:
                        await bot.restrict_chat_member(
                            chat_id=chat_id,
                            user_id=user_id,
                            permissions=types.ChatPermissions(can_send_messages=False)
                        )
                except Exception as e:
                    logger.error(f"Failed to restrict user {user_id} in chat {chat_id}: {e}")
                
                return # Stop processing this message

        await db.add_message(chat_id, "user", user_text)

    if state["timer"]:
        state["timer"].cancel()

    is_quote_reply = False
    if message.reply_to_message and message.reply_to_message.from_user.id == bot.id:
        is_quote_reply = True
    
    if is_quote_reply:
         delay = 0
    else:
        settings = await db.get_chat_settings(chat_id)
        custom_timeout = settings.get("timeout_seconds")
        
        if custom_timeout is not None and isinstance(custom_timeout, int):
             delay = custom_timeout
        else:
             delay = RESPONSE_DELAY
    
    async def delayed_response(chat_id, bot_instance, wait_time):
        if wait_time > 0:
            await asyncio.sleep(wait_time)
        await generate_response(chat_id, bot_instance)

    state["timer"] = asyncio.create_task(delayed_response(chat_id, bot, delay))
