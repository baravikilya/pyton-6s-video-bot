import sys
import os

# Добавляем родительскую директорию в путь поиска модулей
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import aiohttp
from config import RECRAFT_API_KEY

async def generate_image(prompt):
    """Генерация изображения с помощью Recraft API"""
    url = "https://external.api.recraft.ai/v1/images/generations"
    
    headers = {
        "Authorization": f"Bearer {RECRAFT_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "prompt": prompt,
        "negative_prompt": "text, words, letters, inscriptions, signs, symbols, watermarks, characters, numbers",
        "style": "realistic_image",
        "size": "1024x1820"
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload, headers=headers) as response:
            if response.status == 200:
                data = await response.json()
                return data.get("data", [{}])[0].get("url", "")
            else:
                # Обработка ошибок
                error_text = await response.text()
                print(f"Recraft API error: {response.status} - {error_text}")
                return ""
