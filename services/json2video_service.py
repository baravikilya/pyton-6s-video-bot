import sys
import os

# Добавляем родительскую директорию в путь поиска модулей
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import aiohttp
import asyncio
import time
from config import JSON2VIDEO_API_KEY

async def submit_video_job(text, image_url):
    """Отправка задачи на рендеринг видео"""
    url = "https://api.json2video.com/v2/movies"
    
    headers = {
        "x-api-key": JSON2VIDEO_API_KEY,
        "Content-Type": "application/json"
    }
    
    payload = {
        "template": "jEfqlFRye9XASTqdMBba",
        "variables": {
            "text": text,
            "image": image_url
        }
    }
    
    # Отладка для диагностики
    print(f"JSON2Video API request:")
    print(f"URL: {url}")
    print(f"Headers: x-api-key={JSON2VIDEO_API_KEY[:10]}...")
    print(f"Payload: {payload}")

    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload, headers=headers) as response:
            if response.status == 200:
                data = await response.json()
                return data.get("project", "")
            else:
                # Обработка ошибок
                error_text = await response.text()
                print(f"JSON2Video API error: {response.status} - {error_text}")
                return ""

async def check_video_status(project_id):
    """Проверка статуса рендеринга видео"""
    url = f"https://api.json2video.com/v2/movies?project={project_id}"
    
    headers = {
        "x-api-key": JSON2VIDEO_API_KEY,
        "Content-Type": "application/json"
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as response:
            if response.status == 200:
                data = await response.json()
                return data.get("movie", {})
            else:
                # Обработка ошибок
                error_text = await response.text()
                print(f"JSON2Video API error: {response.status} - {error_text}")
                return {}

async def get_video_url(project_id):
    """Получение URL готового видео"""
    # Проверяем статус каждые 5 секунд до 3 минут
    for attempt in range(36):  # 36 попыток по 5 секунд = 3 минуты
        print(f"Попытка {attempt + 1}/36 проверки статуса...")
        movie_data = await check_video_status(project_id)
        status = movie_data.get("status", "")
        print(f"Статус видео: {status}")

        if status == "done":
            video_url = movie_data.get("url", "")
            print(f"Видео готово! URL: {video_url}")
            return video_url
        elif status == "error":
            print(f"Video rendering error: {movie_data.get('message', 'Unknown error')}")
            return ""
        elif status == "processing":
            print("Видео еще рендерится...")
        else:
            print(f"Неизвестный статус: {status}")

        # Ждем 5 секунд перед следующей проверкой
        print("Ждем 5 секунд...")
        await asyncio.sleep(5)

    # Если видео не готово за 3 минуты, возвращаем пустую строку
    print("Видео не готово за 3 минуты")
    return ""
