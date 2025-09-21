import sys
import os

# Добавляем родительскую директорию в путь поиска модулей
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ContextTypes
from database import get_user, update_user_settings

async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    user = update.effective_user
    chat_id = update.effective_chat.id
    
    # Получаем данные пользователя из БД
    db_user = get_user(user.id)
    
    # Если пользователя нет в БД, создаем запись
    if not db_user:
        from database import create_user
        create_user(user.id)
        db_user = get_user(user.id)
    
    # Извлекаем язык и режим из БД (если есть)
    language = db_user[2] if db_user[2] else "— не выбран —"
    mode = db_user[3] if db_user[3] else "— не выбран —"
    
    # Создаем клавиатуру с настройками
    keyboard = [
        [InlineKeyboardButton(f"Язык: {language}", callback_data="set_language")],
        [InlineKeyboardButton(f"Режим: {mode}", callback_data="set_mode")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Отправляем приветственное сообщение
    welcome_text = """🎬 *Автоматический Создатель Контента*

Отправьте тему, и я создам видео для вас"""

    await update.message.reply_text(
        welcome_text,
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

    # Устанавливаем постоянную клавиатуру с кнопкой "📱 Меню"
    menu_keyboard = [
        [KeyboardButton("📱 Меню")]
    ]
    menu_markup = ReplyKeyboardMarkup(menu_keyboard, resize_keyboard=True)

    await update.message.reply_text(
        "\u200B",
        reply_markup=menu_markup
    )
