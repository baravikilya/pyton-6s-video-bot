import sys
import os

# Добавляем родительскую директорию в путь поиска модулей
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from services.openai_service import generate_script_with_tools, generate_image_prompt, generate_title, clean_script_for_render, format_script_for_telegram
from services.recraft_service import generate_image
from services.json2video_service import submit_video_job, get_video_url
from database import get_user
import asyncio

def get_message_object(update):
    """Получение объекта сообщения из update, query или другого объекта"""
    # Если это обычный update с message
    if hasattr(update, 'message') and update.message:
        return update.message
    # Если это callback query
    elif hasattr(update, 'callback_query') and update.callback_query:
        return update.callback_query.message
    # Если это уже message объект (для совместимости)
    elif hasattr(update, 'reply_text'):
        return update
    else:
        return None

def shorten_topic(topic):
    """Создание короткого уникального токена для темы"""
    import hashlib
    # Создаем короткий хэш из темы (первые 8 символов)
    return hashlib.md5(topic.encode('utf-8')).hexdigest()[:8]

async def create_video_handler(update: Update, context: ContextTypes.DEFAULT_TYPE, topic: str, skip_initial_message: bool = False):
    """Обработчик создания видео"""

    # ОЧИЩАЕМ старый контекст перед началом нового процесса
    # Это предотвращает смешивание данных из разных тем
    if "video_data" in context.user_data:
        del context.user_data["video_data"]

    if "short_to_full" in context.user_data:
        del context.user_data["short_to_full"]

    # Проверяем, не идет ли уже обработка этого пользователя
    user_id = update.effective_user.id
    processing_key = f"processing_topic_{user_id}"

    if context.user_data.get(processing_key, False):
        # Если уже обрабатываем - отправляем сообщение и выходим
        message = get_message_object(update)
        if message and not skip_initial_message:
            await message.reply_text(f"⏳ Подожди минутку! Я уже обрабатываю тему \"{topic}\". Дай мне закончить!")
        return

    # Блокируем обработку для этого пользователя
    context.user_data[processing_key] = True

    try:
        # Получаем настройки пользователя
        db_user = get_user(user_id)
        language = db_user[2] if db_user[2] else "русский"
        mode = db_user[3] if db_user[3] else "Автоматический"

        # Генерируем сценарий с использованием инструментов поиска
        script = generate_script_with_tools(topic, language)

        # Проверяем, есть ли ошибка в сгенерированном сценарии
        if script.startswith("❌ Ошибка"):
            message = get_message_object(update)
            if message:
                await message.reply_text(script)
            return

        # Проверяем режим работы
        if mode == "Ручной":
            # В ручном режиме показываем что создаем сценарий
            message = get_message_object(update)
            if message and not skip_initial_message:
                await message.reply_text("✍️ Создаю сценарий...")
            elif message and skip_initial_message:
                await message.reply_text("✍️ Создаю сценарий...")

            # Создаем short_topic для уникального идентификатора
            short_topic = shorten_topic(topic)
            if "short_to_full" not in context.user_data:
                context.user_data["short_to_full"] = {}
            context.user_data["short_to_full"][short_topic] = topic

            # СОХРАНЯЕМ сценарий в контексте для последующего использования при одобрении
            context.user_data["video_data"] = {
                "topic": topic,
                "script": script,
                "language": language,
                "mode": mode
            }

            # В ручном режиме отправляем сценарий на подтверждение
            keyboard = [
                [InlineKeyboardButton("✅ Да", callback_data="approve_script_" + short_topic)],
                [InlineKeyboardButton("🔁 Заново", callback_data="regenerate_script_" + short_topic)]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            # Форматируем сценарий для отображения в Telegram
            formatted_script = format_script_for_telegram(script)
            message_text = "*Сценарий видео*\n\n" + formatted_script + "\n\n"
            message = get_message_object(update)
            if message:
                await message.reply_text(
                    message_text,
                    reply_markup=reply_markup,
                    parse_mode="Markdown"
                )
            return

        # В автоматическом режиме продолжаем без подтверждения
        message = get_message_object(update)
        if message and not skip_initial_message:
            await message.reply_text("✍️ Создаю сценарий...")
        elif message and skip_initial_message:
            await message.reply_text("✍️ Создаю сценарий...")

        await process_script(update, context, topic, script, language, mode)
    except Exception as e:
        message = get_message_object(update)
        if message:
            await message.reply_text(f"❌ Ошибка при создании видео: {str(e)}")
    finally:
        # Снимаем блокировку в любом случае
        context.user_data[processing_key] = False

async def process_script(update: Update, context: ContextTypes.DEFAULT_TYPE, topic: str, script: str, language: str, mode: str):
    """Обработка сценария и генерация названия"""
    message = get_message_object(update)
    if message:
        await message.reply_text("✍️ Пишу название для видео...")
    # Генерируем название видео
    title = generate_title(script, language)

    # Проверяем, есть ли ошибка в сгенерированном заголовке
    if title.startswith("❌ Ошибка"):
        if message:
            await message.reply_text(title)
        return

    # Проверяем режим работы
    if mode == "Ручной":
        # Используем уже созданный short_topic из context
        short_to_full = context.user_data.get("short_to_full", {})
        short_topic = None
        for key in short_to_full:
            if short_to_full[key] == topic:
                short_topic = key
                break
        # Если не нашли, создаем новый
        if not short_topic:
            short_topic = shorten_topic(topic)
            if "short_to_full" not in context.user_data:
                context.user_data["short_to_full"] = {}
            context.user_data["short_to_full"][short_topic] = topic

        # В ручном режиме отправляем название на подтверждение
        keyboard = [
            [InlineKeyboardButton("✅ Да", callback_data="approve_title_" + short_topic)],
            [InlineKeyboardButton("🔁 Заново", callback_data="regenerate_title_" + short_topic)]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        message_text = "*Название видео*\n\n" + title + "\n\n"
        if message:
            await message.reply_text(
                message_text,
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
        # ОБНОВЛЯЕМ контекст вместо пересоздания - сохраняем существующие данные
        if "video_data" not in context.user_data:
            context.user_data["video_data"] = {}

        # Сохраняем существующий script если он отличается
        if "script" not in context.user_data["video_data"]:
            context.user_data["video_data"]["script"] = script

        # Сохраняем другие базовые данные
        context.user_data["video_data"]["topic"] = topic
        context.user_data["video_data"]["title"] = title
        context.user_data["video_data"]["language"] = language
        context.user_data["video_data"]["mode"] = mode

        return

    # В автоматическом режиме продолжаем без подтверждения
    try:
        await process_title(update, context, topic, script, title, language, mode)
    except Exception as e:
        if message:
            await message.reply_text(f"❌ Ошибка при обработке названия: {str(e)}")



async def process_title(update: Update, context: ContextTypes.DEFAULT_TYPE, topic: str, script: str, title: str, language: str, mode: str):
    """Обработка названия и генерация изображения"""
    message = get_message_object(update)
    if message:
        await message.reply_text("🎨 Рисую обложку...")

    # Генерируем промт для изображения
    image_prompt = generate_image_prompt(script)

    # Проверяем, есть ли ошибка в сгенерированном промте
    if image_prompt.startswith("❌ Ошибка"):
        if message:
            await message.reply_text(image_prompt)
        return

    # Генерируем изображение
    image_url = await generate_image(image_prompt)

    # Проверяем режим работы
    if mode == "Ручной":
        # Используем уже созданный short_topic из context
        short_to_full = context.user_data.get("short_to_full", {})
        short_topic = None
        for key in short_to_full:
            if short_to_full[key] == topic:
                short_topic = key
                break
        # Если не нашли, создаем новый
        if not short_topic:
            short_topic = shorten_topic(topic)
            if "short_to_full" not in context.user_data:
                context.user_data["short_to_full"] = {}
            context.user_data["short_to_full"][short_topic] = topic

        # В ручном режиме отправляем изображение на подтверждение
        keyboard = [
            [InlineKeyboardButton("✅ Да", callback_data="approve_image_" + short_topic)],
            [InlineKeyboardButton("🔁 Заново", callback_data="regenerate_image_" + short_topic)]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        # Отправляем изображение
        if message:
            await message.reply_photo(
                photo=image_url,
                caption="Подходит картинка для видео?",
                reply_markup=reply_markup
            )
        # ОБНОВЛЯЕМ контекст вместо пересоздания - сохраняем существующие данные
        if "video_data" not in context.user_data:
            context.user_data["video_data"] = {}

        # Сохраняем существующие данные
        if "script" not in context.user_data["video_data"]:
            context.user_data["video_data"]["script"] = script
        if "title" not in context.user_data["video_data"]:
            context.user_data["video_data"]["title"] = title

        # Сохраняем другие базовые данные
        context.user_data["video_data"]["topic"] = topic
        context.user_data["video_data"]["image_url"] = image_url
        context.user_data["video_data"]["language"] = language
        context.user_data["video_data"]["mode"] = mode

        return

    # В автоматическом режиме продолжаем без подтверждения
    try:
        await process_image(update, context, topic, script, image_url, title, language, mode)
    except Exception as e:
        if message:
            await message.reply_text(f"❌ Ошибка при обработке изображения: {str(e)}")

async def process_image(update: Update, context: ContextTypes.DEFAULT_TYPE, topic: str, script: str, image_url: str, title: str, language: str, mode: str):
    """Обработка изображения и отправка на рендеринг"""

    # БЕРЕМ АКТУАЛЬНЫЕ данные из контекста вместо параметров!
    video_data = context.user_data.get("video_data", {})

    if video_data:
        actual_script = video_data.get("script")
        actual_image_url = video_data.get("image_url")
        actual_title = video_data.get("title")
        actual_topic = video_data.get("topic")
    else:
        # Fallback - используем параметры
        actual_script = script
        actual_image_url = image_url
        actual_title = title
        actual_topic = topic

    message = get_message_object(update)
    # Отправляем сообщение о начале рендеринга
    if message:
        await message.reply_text("🌐 Отправляю задачу на рендер...")

    # Очищаем сценарий для рендеринга (убираем переносы строк и HTML-тэги)
    render_script = clean_script_for_render(actual_script)

    # Отправляем задачу на рендеринг
    project_id = await submit_video_job(render_script, actual_image_url)

    if message:
        await message.reply_text("🌐 Создаю видео. Это может занять до 1 минуты...")

    if not project_id or project_id.startswith("HTTP"):
        if message:
            error_msg = "❌ Ошибка при отправке задачи на рендеринг" + (": " + project_id[:100] if project_id.startswith("HTTP") else "") + ". Попробуйте позже."
            await message.reply_text(error_msg)
        return

    # Получаем URL готового видео
    video_url = await get_video_url(project_id)

    if not video_url:
        if message:
            await message.reply_text("❌ Ошибка при рендеринге видео. Попробуйте позже.")
        return

    # Отправляем готовое видео
    caption_text = f"Название видео:\n```\n{actual_title}\n```"
    if message:
        await message.reply_video(
            video=video_url,
            caption=caption_text,
            parse_mode="MarkdownV2"
        )
