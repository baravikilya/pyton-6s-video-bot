import os
from dotenv import load_dotenv

# Загрузка переменных окружения из .env файла
load_dotenv()

# Telegram Bot Token
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# OpenAI API Key
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Recraft API Key
RECRAFT_API_KEY = os.getenv("RECRAFT_API_KEY")

# JSON2Video API Key
JSON2VIDEO_API_KEY = os.getenv("JSON2VIDEO_API_KEY")

# Webhook URL (опционально)
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

# Host и порт для вебхука
APP_HOST = os.getenv("APP_HOST", "0.0.0.0")
APP_PORT = int(os.getenv("APP_PORT", "8080"))
