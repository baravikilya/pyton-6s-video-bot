import sys
import os
import time

# Добавляем родительскую директорию в путь поиска модулей
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from services.openai_service import generate_script_with_tools, generate_image_prompt, generate_title, format_script_for_telegram, verify_and_format_title
from services.recraft_service import generate_image
from handlers.video_handler import process_script, process_image, process_title

def shorten_topic(topic):
    """Создание короткого уникального токена для темы"""
    import hashlib
    # Создаем короткий хэш из темы (первые 8 символов)
    return hashlib.md5(topic.encode('utf-8')).hexdigest()[:8]

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик callback-запросов"""
    query = update.callback_query
    await query.answer()
    
    # Получаем данные пользователя
    from database import get_user
    db_user = get_user(query.from_user.id)
    language = db_user[2] if db_user[2] else "русский"
    mode = db_user[3] if db_user[3] else "Автоматический"
    
    # Обрабатываем различные типы callback-запросов
    if query.data.startswith("mode_"):
        # Обработка выбора режима
        from handlers.settings_handler import mode_selection_handler
        await mode_selection_handler(update, context)
    
    elif query.data.startswith("approve_script_"):
        # Пользователь одобрил сценарий
        short_topic = query.data.split("_", 2)[2]
        # Получаем полную тему из контекста
        short_to_full = context.user_data.get("short_to_full", {})
        topic = short_to_full.get(short_topic, short_topic)  # Fallback на short_topic если нет в карте

        # Пытаемся получить сценарий из контекста видео данных
        video_data = context.user_data.get("video_data", {})
        approve_script = None
        if video_data and "script" in video_data:
            approve_script = video_data["script"]
        else:
            # Fallback если сценария нет в контексте - генерируем заново
            approve_script = generate_script_with_tools(topic, language)

        # ОБНОВЛЯЕМ контекст с одобренным сценарием вместо создания нового
        if "video_data" not in context.user_data:
            context.user_data["video_data"] = {
                "topic": topic,
                "script": approve_script,
                "language": language,
                "mode": mode
            }
        else:
            context.user_data["video_data"]["topic"] = topic
            context.user_data["video_data"]["script"] = approve_script
            context.user_data["video_data"]["language"] = language
            context.user_data["video_data"]["mode"] = mode

        # Продолжаем процесс создания видео с ЛЮБЫМ сценарием (будет переопределяться в process_script)
        await process_script(query, context, topic, approve_script, language, mode)
    
    elif query.data.startswith("regenerate_script_"):
        # Пользователь хочет перегенерировать сценарий
        short_topic = query.data.split("_", 2)[2]
        # Получаем полную тему из контекста
        short_to_full = context.user_data.get("short_to_full", {})
        topic = short_to_full.get(short_topic, short_topic)  # Fallback на short_topic если нет в карте

        # ГЕНЕРИРУЕМ новый сценарий
        script = generate_script_with_tools(topic, language)

        ## КРИТИЧНЫЙ ИСПРАВЛЕНИЕ: СОХРАНЯЕМ НОВЫЙ СЦЕНАРИЙ В КОНТЕКСТ СРАЗУ!
        # Теперь approve_script_ будет использовать этот новый скрипт
        if "video_data" not in context.user_data:
            context.user_data["video_data"] = {}
        context.user_data["video_data"]["script"] = script
        context.user_data["video_data"]["topic"] = topic
        context.user_data["video_data"]["language"] = language
        context.user_data["video_data"]["mode"] = "Ручной"



        # Создаем новый short_topic если его еще нет в карте
        if topic not in [v for v in short_to_full.values()]:
            short_topic = shorten_topic(topic)
            if "short_to_full" not in context.user_data:
                context.user_data["short_to_full"] = {}
            context.user_data["short_to_full"][short_topic] = topic

        # Отправляем новый сценарий на подтверждение
        keyboard = [
            [InlineKeyboardButton("✅ Да", callback_data="approve_script_" + short_topic)],
            [InlineKeyboardButton("🔁 Заново", callback_data="regenerate_script_" + short_topic)]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        # Удаляем старое сообщение и отправляем новое
        await query.delete_message()

        # Форматируем сценарий для отображения в Telegram
        formatted_script = format_script_for_telegram(script)

        # Отправляем новый сценарий отдельным сообщением
        await query.message.reply_text(
            f"✍️ Создаю сценарий...\n\n{formatted_script}\n\n(Обновлено)",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
    
    elif query.data.startswith("approve_image_"):
        # Пользователь одобрил изображение
        video_data = context.user_data.get("video_data", {})
        if video_data and "image_url" in video_data:
            topic = video_data["topic"]
            script = video_data["script"]
            approve_image_url = video_data["image_url"]
            title = video_data.get("title", topic)

            # ОБНОВЛЯЕМ контекст с одобренным изображением
            context.user_data["video_data"]["image_url"] = approve_image_url

            # Продолжаем процесс создания видео
            await process_image(query, context, topic, script, approve_image_url, title, language, mode)
    
    elif query.data.startswith("regenerate_image_"):
        # Пользователь хочет перегенерировать изображение
        short_topic = query.data.split("_", 2)[2]
        # Получаем полную тему из контекста
        short_to_full = context.user_data.get("short_to_full", {})
        topic = short_to_full.get(short_topic, short_topic)  # Fallback на short_topic если нет в карте

        # Используем СУЩЕСТВУЮЩИЙ сценарий из контекста для генерации нового промта
        video_data = context.user_data.get("video_data", {})
        if video_data and "script" in video_data and "title" in video_data:
            script = video_data["script"]
            title = video_data["title"]
        else:
            # Fallback если сценария нет - генерируем новый (хотя это не должно происходить)
            script = generate_script_with_tools(topic, language)
            title = generate_title(script, language)

        image_prompt = generate_image_prompt(script)
        image_url = await generate_image(image_prompt)

        ## КРИТИЧНЫЙ ИСПРАВЛЕНИЕ: СОХРАНЯЕМ НОВОЕ ИЗОБРАЖЕНИЕ В КОНТЕКСТ!
        if "video_data" not in context.user_data:
            context.user_data["video_data"] = {}
        context.user_data["video_data"]["image_url"] = image_url
        context.user_data["video_data"]["topic"] = topic
        context.user_data["video_data"]["language"] = language
        context.user_data["video_data"]["mode"] = "Ручной"

        # Создаем новый short_topic если его еще нет в карте
        if topic not in [v for v in short_to_full.values()]:
            short_topic = shorten_topic(topic)
            if "short_to_full" not in context.user_data:
                context.user_data["short_to_full"] = {}
            context.user_data["short_to_full"][short_topic] = topic

        # Отправляем новое изображение на подтверждение
        keyboard = [
            [InlineKeyboardButton("✅ Да", callback_data="approve_image_" + short_topic)],
            [InlineKeyboardButton("🔁 Заново", callback_data="regenerate_image_" + short_topic)]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        # Удаляем старое сообщение с изображением
        await query.delete_message()

        # Отправляем новое изображение отдельным сообщением
        await query.message.reply_photo(
            photo=image_url,
            caption="Подходит картинка для видео? (Обновлено)",
            reply_markup=reply_markup
        )
    
    elif query.data.startswith("approve_title_"):
        # Пользователь одобрил название
        video_data = context.user_data.get("video_data", {})
        if video_data and "title" in video_data:
            topic = video_data["topic"]
            script = video_data["script"]
            approve_title = video_data["title"]

            # ОБНОВЛЯЕМ контекст с одобренным названием
            context.user_data["video_data"]["title"] = approve_title

            # Продолжаем процесс создания видео
            await process_title(query, context, topic, script, approve_title, language, mode)
    
    elif query.data.startswith("regenerate_title_"):
        # Пользователь хочет перегенерировать название
        short_topic = query.data.split("_", 2)[2]
        # Получаем полную тему из контекста
        short_to_full = context.user_data.get("short_to_full", {})
        topic = short_to_full.get(short_topic, short_topic)  # Fallback на short_topic если нет в карте

        # Используем СУЩЕСТВУЮЩИЙ сценарий из контекста для генерации нового названия
        video_data = context.user_data.get("video_data", {})
        if video_data and "script" in video_data:
            script = video_data["script"]
        else:
            # Fallback если сценария нет - генерируем новый (хотя это не должно происходить)
            script = generate_script_with_tools(topic, language)

        title = generate_title(script, language)

        # Проверяем и форматируем название
        title_verified = verify_and_format_title(title, language)
        if title_verified.startswith("❌ Ошибка"):
            title_verified = title

        ## КРИТИЧНЫЙ ИСПРАВЛЕНИЕ: СОХРАНЯЕМ НОВОЕ НАЗВАНИЕ В КОНТЕКСТ!
        if "video_data" not in context.user_data:
            context.user_data["video_data"] = {}
        context.user_data["video_data"]["title"] = title_verified
        context.user_data["video_data"]["topic"] = topic
        context.user_data["video_data"]["language"] = language
        context.user_data["video_data"]["mode"] = "Ручной"

        # Создаем новый short_topic если его еще нет в карте
        if topic not in [v for v in short_to_full.values()]:
            short_topic = shorten_topic(topic)
            if "short_to_full" not in context.user_data:
                context.user_data["short_to_full"] = {}
            context.user_data["short_to_full"][short_topic] = topic

        # Отправляем новое название на подтверждение
        keyboard = [
            [InlineKeyboardButton("✅ Да", callback_data="approve_title_" + short_topic)],
            [InlineKeyboardButton("🔁 Заново", callback_data="regenerate_title_" + short_topic)]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        # Удаляем старое сообщение и отправляем новое
        await query.delete_message()

        # Отправляем новое название отдельным сообщением
        await query.message.reply_text(
            f"✍️ Пишу название для видео...\n\n{title_verified}\n\n(Обновлено)",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
