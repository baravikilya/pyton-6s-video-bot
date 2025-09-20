import sys
import os

# Добавляем родительскую директорию в путь поиска модулей
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import time
import asyncio

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database import update_user_settings

# Варианты режимов работы
MODES = ["Автоматический", "Ручной"]

async def settings_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик callback для настроек"""
    query = update.callback_query
    await query.answer()

    if query.data == "set_language":
        # Запрашиваем у пользователя язык
        await query.edit_message_text(
            "Введите язык для видео:",
        )
        # Устанавливаем состояние ожидания ввода языка
        context.user_data["awaiting_input"] = "language"
        # Сохраняем ID сообщения с запросом языка для последующего удаления
        context.user_data["language_request_message_id"] = query.message.message_id
        # Сохраняем временную метку для авто-очистки
        context.user_data["language_request_timestamp"] = time.time()
    
    elif query.data == "set_mode":
        # Создаем клавиатуру с вариантами режимов
        keyboard = [
            [InlineKeyboardButton(mode, callback_data=f"mode_{mode}")]
            for mode in MODES
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "Выберите режим работы:",
            reply_markup=reply_markup
        )

async def mode_selection_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик выбора режима"""
    query = update.callback_query
    await query.answer()
    
    # Извлекаем выбранный режим из callback_data
    selected_mode = query.data.split("_", 1)[1]
    
    # Обновляем настройки пользователя в БД
    update_user_settings(query.from_user.id, mode=selected_mode)
    
    # Получаем текущие настройки пользователя
    from database import get_user
    db_user = get_user(query.from_user.id)
    language = db_user[2] if db_user[2] else "— не выбран —"
    
    # Обновляем сообщение с настройками
    keyboard = [
        [InlineKeyboardButton(f"Язык: {language}", callback_data="set_language")],
        [InlineKeyboardButton(f"Режим: {selected_mode}", callback_data="set_mode")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        """🎬 *Автоматический Создатель Контента*

Отправьте тему, и я создам видео для вас""",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def language_input_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик ввода языка пользователем"""
    user_text = update.message.text

    # Проверяем, не нажата ли кнопка "📱 Меню"
    if user_text == "📱 Меню":
        from handlers.start_handler import start_handler
        await start_handler(update, context)
        return

    # Чистим старое состояние ожидания, если прошло слишком много времени
    last_message_time = context.user_data.get("language_request_timestamp")
    if last_message_time and (asyncio.get_event_loop().time() - last_message_time) > 300:  # 5 минут
        context.user_data["awaiting_input"] = None

    # Проверяем, ожидаем ли мы ввод языка
    if context.user_data.get("awaiting_input") == "language":
        # Получаем введенный язык
        language = update.message.text
        
        # Обновляем настройки пользователя в БД
        update_user_settings(update.effective_user.id, language=language)
        
        # Сбрасываем состояние ожидания
        context.user_data["awaiting_input"] = None

        # Получаем текущие настройки пользователя
        from database import get_user
        db_user = get_user(update.effective_user.id)
        mode = db_user[3] if db_user[3] else "— не выбран —"

        # Удаляем исходное сообщение пользователя и сообщение с запросом языка
        try:
            # Удаляем ответ пользователя
            await update.message.delete()

            # Удаляем сообщение с запросом языка если сохранили его ID
            if "language_request_message_id" in context.user_data:
                try:
                    await context.bot.delete_message(
                        chat_id=update.effective_chat.id,
                        message_id=context.user_data["language_request_message_id"]
                    )
                except:
                    pass  # Игнорируем если не удалось удалить

            # Находим сообщение с настройками и обновляем его
            if "settings_message_id" in context.user_data:
                chat_id = update.effective_chat.id
                keyboard = [
                    [InlineKeyboardButton(f"Язык: {language}", callback_data="set_language")],
                    [InlineKeyboardButton(f"Режим: {mode}", callback_data="set_mode")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)

                await context.bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=context.user_data["settings_message_id"],
                    text="""🎬 *Автоматический Создатель Контента*

Отправьте тему, и я создам видео для вас""",
                    reply_markup=reply_markup,
                    parse_mode="Markdown"
                )
            else:
                # Fallback - новое сообщение
                keyboard = [
                    [InlineKeyboardButton(f"Язык: {language}", callback_data="set_language")],
                    [InlineKeyboardButton(f"Режим: {mode}", callback_data="set_mode")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)

                await update.message.reply_text(
                    text="""🎬 *Автоматический Создатель Контента*

Отправьте тему, и я создам видео для вас""",
                    reply_markup=reply_markup,
                    parse_mode="Markdown"
                )

        except Exception as e:
            # Если удаление не удалось, просто продолжаем в обычном режиме
            keyboard = [
                [InlineKeyboardButton(f"Язык: {language}", callback_data="set_language")],
                [InlineKeyboardButton(f"Режим: {mode}", callback_data="set_mode")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await update.message.reply_text(
                """🎬 *Автоматический Создатель Контента*

Отправьте тему, и я создам видео для вас""",
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
    else:
        # Если не ожидаем ввод языка, обрабатываем как тему для видео
        await handle_topic_input(update, context)

async def handle_topic_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик ввода темы для видео"""
    # Получаем тему от пользователя
    topic = update.message.text

    # Импортируем обработчик создания видео без дополнительного сообщения
    from handlers.video_handler import create_video_handler
    await create_video_handler(update, context, topic, skip_initial_message=True)
