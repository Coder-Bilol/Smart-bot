import os
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# Bot configuration
API_TOKEN = os.getenv("TG_TOKEN")
VOIDAI_API_KEY = os.getenv("VOIDAI_API_KEY")
RESPONSE_DELAY = int(os.getenv("RESPONSE_DELAY", 5))  # Default 5 seconds

# Application configuration
MAX_HISTORY_MESSAGES = 50