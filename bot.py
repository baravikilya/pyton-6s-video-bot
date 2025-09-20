import asyncio
import sys
import os

# Добавляем текущую директорию в путь поиска модулей
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from config import TELEGRAM_BOT_TOKEN, WEBHOOK_URL, APP_HOST, APP_PORT
from database import init_db
from handlers.start_handler import start_handler
from handlers.settings_handler import language_input_handler, settings_callback_handler
from handlers.callback_handler import callback_handler

def main():
    """Основная функция для запуска бота"""
    # Инициализация базы данных
    init_db()
    
    # Создание приложения бота
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # Регистрация обработчиков команд
    application.add_handler(CommandHandler("start", start_handler))
    
    # Регистрация обработчиков callback-запросов для настроек
    application.add_handler(CallbackQueryHandler(settings_callback_handler, pattern="^(set_language|set_mode)$"))
    
    # Регистрация обработчиков callback-запросов для режимов
    application.add_handler(CallbackQueryHandler(callback_handler))
    
    # Регистрация обработчиков сообщений
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, language_input_handler))
    
    # Запуск бота
    if WEBHOOK_URL:
        # Используем вебхук
        application.run_webhook(
            listen=APP_HOST,
            port=APP_PORT,
            url_path=TELEGRAM_BOT_TOKEN,
            webhook_url=f"{WEBHOOK_URL}/{TELEGRAM_BOT_TOKEN}"
        )
    else:
        # Используем polling
        application.run_polling()

if __name__ == "__main__":
    main()