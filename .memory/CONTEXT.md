# Context

## Environment
- **OS**: Windows / Linux
- **Runtime**: Python 3.10+
- **Configuration**: `.env` файл (не коммитится).

## Tech Stack
- **Framework**: `aiogram` 3.x (Asyncio)
- **Database**: `aiosqlite` (SQLite 3)
- **LLM Client**: `openai` (Python SDK) -> OpenRouter API. **Important**: каждая модель требует свой уникальный API-ключ.
- **Utilities**: `python-dotenv`

## Commands
### User/Public
- `/start`: Приветствие.

### Admin
- `/startconv`: Включить режим разговора.
- `/stopconv`: Выключить режим разговора.
- `/role [text]`: Установить роль.
- `/goal [text]`: Установить цель.
- `/model`: Выбор модели LLM.
- `/timeout [sec]`: Настройка задержки.
- `/statusconv`: Статус настроек.

## Quality Policy
- **Async First**: Весь I/O (БД, Сеть) должен быть асинхронным.
- **Error Handling**: Бот не должен падать при ошибках API; ошибки логируются в `bot.log`.
- **Typing**: Использовать Type Hints где возможно.
- **Clean Code**: Следовать PEP 8.