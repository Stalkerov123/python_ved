"""
Конфигурационный файл для Telegram бота.
"""

import os
from dotenv import load_dotenv

# Загрузка переменных окружения из .env файла
load_dotenv()

# Настройки бота
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN")

# Настройки веб-хука
USE_WEBHOOK = os.getenv("USE_WEBHOOK", "False").lower() == "true"
WEBHOOK_HOST = os.getenv("WEBHOOK_HOST", "example.com")
WEBHOOK_PATH = os.getenv("WEBHOOK_PATH", f"/webhook/{BOT_TOKEN}")
WEBHOOK_URL = os.getenv("WEBHOOK_URL", f"https://{WEBHOOK_HOST}")

# Настройки веб-сервера
WEBAPP_HOST = os.getenv("WEBAPP_HOST", "localhost")
WEBAPP_PORT = int(os.getenv("WEBAPP_PORT", 8000))

# Настройки парсера ВГУИТ
VSUET_BASE_URL = os.getenv("VSUET_BASE_URL", "https://rating.vsuet.ru/web/Ved/")

# Пути к директориям
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
EXPORT_DIR = os.path.join(BASE_DIR, "exports")

# Создаем директорию для экспорта, если не существует
os.makedirs(EXPORT_DIR, exist_ok=True)