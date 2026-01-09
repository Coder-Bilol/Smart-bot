import os
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# Bot configuration
API_TOKEN = os.getenv("TG_TOKEN")
# OPENROUTER_API_KEY removed in favor of per-model keys
RESPONSE_DELAY = int(os.getenv("RESPONSE_DELAY", 5))  # Default 5 seconds

# Application configuration
MAX_HISTORY_MESSAGES = 50

# LLM Configuration
# Map model IDs to their display names and specific environment variable names for keys
MODEL_CONFIGS = {
    "z-ai/glm-4.5-air:free": {
        "name": "Z.ai GLM 4.5 Air (Free)",
        "api_key": os.getenv("OPENROUTER_KEY_ZAI")
    },
    "qwen/qwen3-4b:free": {
        "name": "Qwen 3 (Free)",
        "api_key": os.getenv("OPENROUTER_KEY_QWEN")
    },
    "moonshotai/kimi-vl-a3b-thinking:free": {
        "name": "Kimi VL A3B Thinking (Free)",
        "api_key": os.getenv("OPENROUTER_KEY_KIMI")
    },
    "xiaomi/mimo-v2-flash:free": {
        "name": "Xiaomi MiMo V2 (Free)",
        "api_key": os.getenv("OPENROUTER_KEY_XIAOMI")
    },
    "deepseek/deepseek-chat-v3-0324:free": {
        "name": "DeepSeek V3 Chat (Free)",
        "api_key": os.getenv("OPENROUTER_KEY_DEEPSEEK")
    }
}

# For backward compatibility / easy access to names
AVAILABLE_MODELS = {k: v["name"] for k, v in MODEL_CONFIGS.items()}

DEFAULT_MODEL = "z-ai/glm-4.5-air:free"