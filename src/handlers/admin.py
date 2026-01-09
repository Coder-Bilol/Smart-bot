from aiogram import Router, types
from aiogram.filters import Command, CommandObject
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

from config import RESPONSE_DELAY, AVAILABLE_MODELS
from logging_config import logger
from chat_state_manager import db
from utils.admin import is_admin
from utils.prompts import read_prompt_file

router = Router()

@router.message(Command("role"))
async def cmd_role(message: types.Message, command: CommandObject):
    if not await is_admin(message):
        await message.answer("🚫 Only admins can change the role.")
        return

    chat_id = message.chat.id
    custom_role = command.args
    
    if not custom_role:
        await db.update_chat_settings(chat_id, custom_role="")
        await message.answer("🔄 Custom role reset.")
        logger.info(f"Custom role reset for chat {chat_id}")
    else:
        await db.update_chat_settings(chat_id, custom_role=custom_role)
        await message.answer(f"🎭 Custom role set to: {custom_role}")
        logger.info(f"Custom role set for chat {chat_id}: {custom_role}")

@router.message(Command("goal"))
async def cmd_goal(message: types.Message, command: CommandObject):
    if not await is_admin(message):
        await message.answer("🚫 Only admins can change the goal.")
        return

    chat_id = message.chat.id
    custom_goal = command.args

    if not custom_goal:
        await db.update_chat_settings(chat_id, custom_goal="")
        await message.answer("🔄 Custom goal reset.")
        logger.info(f"Custom goal reset for chat {chat_id}")
    else:
        await db.update_chat_settings(chat_id, custom_goal=custom_goal)
        await message.answer(f"🥅 Custom goal set.")
        logger.info(f"Custom goal set for chat {chat_id}")

@router.message(Command("timeout"))
async def cmd_timeout(message: types.Message, command: CommandObject):
    if not await is_admin(message):
        await message.answer("🚫 Only admins can change the timeout.")
        return

    chat_id = message.chat.id
    
    if not command.args:
        await db.update_chat_settings(chat_id, timeout_seconds=None)
        await message.answer("🔄 Timeout reset to default.")
        logger.info(f"Timeout reset for chat {chat_id}")
    else:
        try:
            timeout = int(command.args)
            if timeout < 0:
                raise ValueError
            
            await db.update_chat_settings(chat_id, timeout_seconds=timeout)
            await message.answer(f"⏱ Timeout set to: {timeout} seconds")
            logger.info(f"Timeout set for chat {chat_id}: {timeout}")
        except ValueError:
            await message.answer("⚠ Please provide a valid positive integer for seconds.")

@router.message(Command("model"))
async def cmd_model(message: types.Message):
    if not await is_admin(message):
        await message.answer("🚫 Only admins can change the model.")
        return
    
    chat_id = message.chat.id
    settings = await db.get_chat_settings(chat_id)
    current_model = settings.get("model")
    if not current_model:
        current_model = list(AVAILABLE_MODELS.keys())[0]
    
    keyboard = []
    for model_id, model_name in AVAILABLE_MODELS.items():
        text = f"✅ {model_name}" if model_id == current_model else model_name
        keyboard.append([InlineKeyboardButton(text=text, callback_data=f"set_model:{model_id}")])
    
    markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    await message.answer(f"🧠 **Select AI Model**\nCurrent model: `{AVAILABLE_MODELS.get(current_model, current_model)}`", reply_markup=markup, parse_mode="Markdown")

@router.callback_query()
async def model_callback_handler(callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    chat_id = callback_query.message.chat.id
    
    # Simple explicit check without using message object
    chat_member = await callback_query.bot.get_chat_member(chat_id, user_id)
    if chat_member.status not in ["administrator", "creator"]:
        await callback_query.answer("🚫 Only admins can change the model.", show_alert=True)
        return

    data = callback_query.data
    if data.startswith("set_model:"):
        model_id = data.split(":", 1)[1]
        
        if model_id in AVAILABLE_MODELS:
            await db.update_chat_settings(chat_id, model=model_id)
            model_name = AVAILABLE_MODELS[model_id]
            
            await callback_query.message.edit_text(f"🧠 **Model Updated**\nNew model: `{model_name}`", parse_mode="Markdown")
            await callback_query.answer(f"Model set to {model_name}")
            logger.info(f"Model set to {model_id} for chat {chat_id} via callback")
        else:
            await callback_query.answer("⚠ Invalid model selected.", show_alert=True)
    
    elif data.startswith("set_mod_action:"):
        action = data.split(":", 1)[1]
        await db.update_chat_settings(chat_id, mod_action=action)
        await callback_query.message.edit_text(
            f"🛡 **Moderation Updated**\nAction for violations: **{action.capitalize()}**", 
            parse_mode="Markdown"
        )
        await callback_query.answer(f"Action set to {action}")
        logger.info(f"Moderation action set to {action} for chat {chat_id}")

@router.message(Command("statusconv"))
async def cmd_statusconv(message: types.Message):
    if not await is_admin(message):
        await message.answer("🚫 Only admins can view the status.")
        return

    chat_id = message.chat.id
    
    base_role = read_prompt_file("role_prompt.md")
    base_goal = read_prompt_file("goal_prompt.md")
    
    settings = await db.get_chat_settings(chat_id)
    custom_role = settings.get("custom_role", "")
    custom_goal = settings.get("custom_goal", "")
    pk_timeout = settings.get("timeout_seconds")
    is_active = settings.get("is_active", False)
    
    timeout_display = f"{pk_timeout}s" if pk_timeout is not None else f"{RESPONSE_DELAY}s (default)"
    status_text = "🟢 ACTIVE" if is_active else "🔴 INACTIVE"
    
    status_msg = (
        f"📋 **Current Conversation Status**\n"
        f"Status: **{status_text}**\n\n"
        f"**# Role**\n"
        f"{base_role}\n"
        f"{custom_role}\n\n"
        f"**# Goal**\n"
        f"{base_goal}\n"
        f"{custom_goal}\n\n"
        f"**# Timeout**\n"
        f"{timeout_display}\n\n"
        f"**# Model**\n"
        f"{AVAILABLE_MODELS.get(settings.get('model'), settings.get('model'))}"
    )
    
    await message.answer(status_msg, parse_mode="Markdown")

@router.message(Command("mod_settings"))
async def cmd_mod_settings(message: types.Message):
    if not await is_admin(message):
        await message.answer("🚫 Only admins can change moderation settings.")
        return
    
    chat_id = message.chat.id
    settings = await db.get_chat_settings(chat_id)
    current_action = settings.get("mod_action", "mute")
    strict_threshold = settings.get("strict_threshold", 2)
    
    keyboard = [
        [InlineKeyboardButton(text=f"{'✅ ' if current_action == 'mute' else ''}Mute", callback_data="set_mod_action:mute")],
        [InlineKeyboardButton(text=f"{'✅ ' if current_action == 'ban' else ''}Ban", callback_data="set_mod_action:ban")]
    ]
    
    markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    await message.answer(
        f"🛡 **Настройки модерации**\n"
        f"Действие при нарушениях: **{current_action.capitalize()}**\n"
        f"Порог нарушений: **{strict_threshold}**\n\n"
        f"Выберите действие:",
        reply_markup=markup,
        parse_mode="Markdown"
    )

@router.message(Command("graylist"))
async def cmd_graylist(message: types.Message):
    chat_id = message.chat.id
    bot = message.bot
    grey_list = await db.get_grey_list(chat_id)
    
    if not grey_list:
        await message.answer("📋 Серый список пуст. Нарушителей нет.")
        return
    
    lines = ["📋 **Серый список нарушителей:**\n"]
    for i, entry in enumerate(grey_list, 1):
        user_id = entry["user_id"]
        count = entry["violation_count"]
        
        # Try to get user info from Telegram
        try:
            chat_member = await bot.get_chat_member(chat_id, user_id)
            user = chat_member.user
            name = user.full_name or "Без имени"
            username = f"@{user.username}" if user.username else "нет никнейма"
            user_info = f"{name} ({username})"
        except Exception:
            user_info = f"Пользователь `{user_id}` (недоступен)"
        
        lines.append(f"{i}. {user_info} — **{count}** нарушений")
    
    await message.answer("\n".join(lines), parse_mode="Markdown")

@router.message(Command("strict"))
async def cmd_strict(message: types.Message, command: CommandObject):
    if not await is_admin(message):
        await message.answer("🚫 Только админы могут менять порог нарушений.")
        return

    chat_id = message.chat.id
    
    if not command.args:
        settings = await db.get_chat_settings(chat_id)
        current_threshold = settings.get("strict_threshold", 2)
        await message.answer(
            f"⚖️ Текущий порог: **{current_threshold}** нарушений до ограничения.\n"
            "Используйте `/strict <число>` чтобы изменить.",
            parse_mode="Markdown"
        )
        return
    
    try:
        threshold = int(command.args)
        if threshold < 1:
            raise ValueError
        
        await db.update_chat_settings(chat_id, strict_threshold=threshold)
        await message.answer(f"⚖️ Порог изменён на **{threshold}** нарушений.", parse_mode="Markdown")
        logger.info(f"Strict threshold set to {threshold} for chat {chat_id}")
    except ValueError:
        await message.answer("⚠ Укажите положительное целое число.")

@router.message(Command("groupabout"))
async def cmd_groupabout(message: types.Message, command: CommandObject):
    if not await is_admin(message):
        await message.answer("🚫 Только админы группы могут настраивать специфику чата.")
        return

    chat_id = message.chat.id
    new_context = command.args
    
    if not new_context:
        settings = await db.get_chat_settings(chat_id)
        current_ctx = settings.get("chat_context", "")
        if current_ctx:
            await message.answer(
                f"📝 **Текущая специфика чата:**\n\n{current_ctx}\n\n"
                "Чтобы изменить, напишите: `/groupabout [ваш текст]`",
                parse_mode="Markdown"
            )
        else:
            await message.answer(
                "📝 Специфика чата еще не задана. Бот использует общие правила модерации.\n\n"
                "Напишите `/groupabout [текст]`, чтобы задать тематику сообщества.",
                parse_mode="Markdown"
            )
        return

    await db.update_chat_settings(chat_id, chat_context=new_context)
    await message.answer(f"✅ **Специфика чата успешно обновлена!** Теперь ИИ модератор будет учитывать этот контекст.")
    logger.info(f"Chat context updated for group {chat_id}")
