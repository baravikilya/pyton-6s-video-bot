import sys
import os

# Добавляем родительскую директорию в путь поиска модулей
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import openai
from config import OPENAI_API_KEY
import json

# Инициализация клиента OpenAI
client = openai.OpenAI(api_key=OPENAI_API_KEY)

def log_openai_response(response_type, prompt, response):
    """Логирование ответов OpenAI для отладки"""
    import time
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n[{timestamp}] OPENAI RESPONSE - {response_type}")
    print(f"INPUT TEXT: {prompt}")
    print(f"OUTPUT: {response[:1000]}...")
    print("="*60)

def clean_script_for_render(script):
    """Подготовка сценария для рендеринга (убираем только переносы строк, HTML-тэги оставляем)"""
    # Удаляем только переносы строк
    cleaned = script.replace("\\n", " ").replace("\n", " ")
    return cleaned.strip()

def format_script_for_telegram(script):
    """Подготовка сценария для отображения в Telegram (заменяем HTML-тэги на *)"""
    # Заменяем HTML выделения на жирный текст Telegram
    return script.replace('<span class="highlight">', '*').replace('</span>', '*')

def verify_and_format_story(text, language):
    """Проверка и форматирование сгенерированного сценария"""
    prompt = f"""
Твоя задача — отформатировать текст на {language} языке по пяти строгим правилам.

1. Не переписывай текст, ничего не придумывай.
2. Проверь контекст. Он должен подходить для носителей {language} языка и описывать события 90х. Исправь, если это не так.
3. Проверь финал текста. Он должен заканчиваться ОДНИМ коротким словом-призывом к подписке. Исправь, если это не так.
Примеры: `Subscribe!` (en), `Subskrybuj!` (pl), `Abonnieren!` (de), `Abonnez-vous !` (fr), `¡Suscríbete!` (es).
4. Выдели два самых интересных фрагмента (по 1-2 предложения из первой и второй половины текста) тегами `<span class="highlight">` и `</span>`.
5. Твой ответ — только итоговый отформатированный текст на {language} языке, длина 80-90 слов, слитный текст без абзацев, без объяснений и лишних слов.

Текст для проверки:
{text}
"""

    try:
        # Используем новый Responses API без веб-поиска для проверки
        response = client.responses.create(
            model="gpt-4.1-mini",
            input=[
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            text={
                "format": {
                    "type": "text"
                }
            },
            temperature=0.3,
            max_output_tokens=1024,
            top_p=1
        )

        result = response.output[0].content[0].text.strip()
        log_openai_response("STORY_VERIFICATION", prompt, result)
        return result
    except openai.PermissionDeniedError as e:
        if "unsupported_country_region_territory" in str(e):
            return "❌ Ошибка: Ваша страна не поддерживается OpenAI. Попробуйте использовать VPN."
        else:
            return "❌ Ошибка доступа к OpenAI. Попробуйте позже."
    except Exception as e:
        print(f"❌ Ошибка при проверке сценария: {str(e)}")
        log_openai_response("VERIFICATION_ERROR", prompt, str(e))
        return text  # Возвращаем оригинальный текст в случае ошибки

def generate_script_with_tools(topic, language):
    """Генерация сценария с использованием встроенного веб-поиска OpenAI"""
    prompt = f"""
Ты — профессиональный сценарист и носитель {language} языка. Твоя задача — написать текст для короткого захватывающего видео на YouTube.

Требования к тексту:
1.  **Язык**: Текст должен быть написан безупречно на {language} языке, как для носителей.
2.  **Место**: Целевая аудитория - носители {language} языка, пиши историю в их контексте.
3.  **Время**: Если точно не известно, когда произошла история, считай, что она произошла в 90х.
4.  **Длина**: строго 80-90 слов. Текст должен быть слитным, без абзацев.
5.  **Структура**:
    - Начни с года и места (например: "In 2023, in the city of...").
    - Опиши невероятное событие, уникальную находку или рекорд, связанный с темой. Используй цифры и неожиданные факты.
6.  **Стиль**: Энергичный, сенсационный, информативный. Текст должен удерживать внимание зрителя до последней секунды.
7.  **Призыв к действию**: В самом конце текста добавь только слово "Подпишись!", что значит нажать на кнопку подписаться, на {language} языке.
Не добавляй конструкций типа "если вам понравилось видео, поставьте лайк и подпишитесь" или "подпишитесь, чтобы ...", просто "Подпишись!" и все.
8.  **Источники**: Если возможно, используй поисковую функцию для получения реальных фактов. Не придумывай информацию, проверяй с помощью tools.
9.  **Формат ответа**: Ответ должен содержать только сгенерированный текст. Никаких приветствий, заголовков ссылок на источники или объяснений.

Тема истории:
{topic}
"""

    try:
        # Дебаггинг: проверяем не двойной ли вызов
        import time
        current_time = time.time()
        print(f"DEBUG: Вызов generate_script_with_tools {current_time} для темы: {topic}")

        # Шаг 1: Генерация черновика сценария с веб-поиском
        response = client.responses.create(
            model="gpt-4.1-mini",
            input=[
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            text={
                "format": {
                    "type": "text"
                }
            },
            temperature=0.7,
            max_output_tokens=2048,
            top_p=1,
            tools=[
                {
                    "type": "web_search",
                    "user_location": {
                        "type": "approximate"
                    },
                    "search_context_size": "medium"
                }
            ],
            include=["web_search_call.action.sources"]
        )

        # Получаем черновик сценария
        draft_script = response.output[1].content[0].text.strip()
        log_openai_response("SCRIPT_DRAFT", prompt, draft_script)

        # Шаг 2: Проверка и форматирование сценария
        final_script = verify_and_format_story(draft_script, language)
        log_openai_response("SCRIPT_FINAL", draft_script, final_script)

        return final_script

    except openai.PermissionDeniedError as e:
        if "unsupported_country_region_territory" in str(e):
            return "❌ Ошибка: Ваша страна не поддерживается OpenAI. Попробуйте использовать VPN."
        else:
            return "❌ Ошибка доступа к OpenAI. Попробуйте позже."
    except Exception as e:
        print(f"❌ Ошибка при генерации сценария с веб-поиском: {str(e)}")
        log_openai_response("SCRIPT_ERROR", prompt, str(e))
        return "❌ Ошибка при генерации сценария. Попробуйте позже."

def generate_image_prompt(story):
    """Генерация промта для изображения на основе истории (обновленная версия)"""
    prompt = f"""
Твоя роль:
Ты — ИИ-художник, эксперт в создании промтов для нейросетей (таких как Midjourney, Stable Diffusion).

Твоя задача:
Проанализировать текст истории и создать один детализированный промт на английском языке для генерации атмосферного, кинематографичного изображения.

Правила создания промта:
1.  **Стиль 90-х**: обязательно стилизуй изображение под эстетику 90-х. Используй ключевые слова: '90s aesthetic, analog film photo, grainy, cinematic shot on 35mm film, muted colors'.
2.  **Реалистичность**: Изображение должно подчинятся законал физики, тяжелые объекты всегда лежат, человек не может держать тяжелый объект.
3.  **Без текста**: Добавь в конец '--no text words letters' для исключения текста на изображении.
4.  **Язык**: Промт должен быть исключительно на английском языке.
5.  **Формат ответа**: Только промт. Никаких объяснений, заголовков или лишних фраз.

История для анализа:
{story}
"""

    try:
        response = client.responses.create(
            model="gpt-4.1-mini",
            input=[
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            text={
                "format": {
                    "type": "text"
                }
            },
            temperature=0.7,
            max_output_tokens=1024,
            top_p=1
        )

        result = response.output[0].content[0].text.strip()
        log_openai_response("IMAGE_PROMPT", prompt, result)
        return result
    except openai.PermissionDeniedError as e:
        if "unsupported_country_region_territory" in str(e):
            return "❌ Ошибка: Ваша страна не поддерживается OpenAI. Попробуйте использовать VPN."
        else:
            return "❌ Ошибка доступа к OpenAI. Попробуйте позже."
    except Exception as e:
        return f"❌ Ошибка при генерации промта для изображения: {str(e)}"

def generate_title(text, language):
    """Генерация заголовка для видео (обновленная версия)"""
    prompt = f"""
Ты — SMM-маркетолог, эксперт по виральному контенту.
Твоя задача — создать короткий, интригующий заголовок для видео на {language} языке на основе предоставленного текста.

Требования:
1.  **Длина**: Строго от 35 до 40 символов.
2.  **Стиль**: Максимально цепляющий и интригующий, вызывающий желание немедленно посмотреть видео.
3.  **Язык**: Заголовок должен быть на {language} языке.
4.  **Формат ответа**: Только заголовок, без кавычек и дополнительных пояснений.

Текст для анализа:
{text}
"""

    try:
        response = client.responses.create(
            model="gpt-4.1-mini",
            input=[
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            text={
                "format": {
                    "type": "text"
                }
            },
            temperature=0.7,
            max_output_tokens=512,
            top_p=1
        )

        result = response.output[0].content[0].text.strip()
        log_openai_response("TITLE", prompt, result)
        return result
    except openai.PermissionDeniedError as e:
        if "unsupported_country_region_territory" in str(e):
            return "❌ Ошибка: Ваша страна не поддерживается OpenAI. Попробуйте использовать VPN."
        else:
            return "❌ Ошибка доступа к OpenAI. Попробуйте позже."
    except Exception as e:
        return f"❌ Ошибка при генерации заголовка: {str(e)}"
