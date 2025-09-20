# 🎬 Телеграм-бот для автоматического создания видео

Этот бот позволяет автоматически создавать короткие видео на основе текстовых тем и шаблонов. Бот интегрирован с OpenAI, Recraft и JSON2Video API для генерации сценариев, изображений и финального видео.

## 🚀 Начало работы

### Предварительные требования

- Python 3.9 или выше
- Токены API для OpenAI, Recraft и JSON2Video
- Телеграм-бот (токен от @BotFather)

### Установка

1. Клонируйте репозиторий:
   ```bash
   git clone <repo-url>
   cd <repo-name>
   ```

2. Установите зависимости:
   ```bash
   pip install -r requirements.txt
   ```

3. Создайте файл `.env` в корне проекта и добавьте в него свои API ключи:
   ```
   TELEGRAM_BOT_TOKEN=your_telegram_bot_token
   OPENAI_API_KEY=your_openai_api_key
   RECRAFT_API_KEY=your_recraft_api_key
   JSON2VIDEO_API_KEY=your_json2video_api_key
   
   # Опционально для вебхука
   WEBHOOK_URL=
   
   # По умолчанию
   APP_HOST=0.0.0.0
   APP_PORT=8080
   ```

### Запуск

Для запуска бота используйте команду:

```bash
python bot.py
```

Бот будет запущен в режиме polling и будет готов принимать сообщения.

## 🎯 Использование

1. Найдите бота в Telegram
2. Отправьте команду `/start` для запуска
3. Настройте параметры (язык, режим)
4. Отправьте тему для видео
5. Получите готовое видео

## 🔄 Режимы работы

### Автоматический режим
Все шаги выполняются без участия пользователя

### Ручной режим
Каждый шаг подтверждается пользователем

## ⚙️ Настройки

### Язык
Выбор языка для перевода текста

### Режим работы
- Автоматический
- Ручной

## 📁 Структура проекта

```
.
├── bot.py                 # Основной файл бота
├── config.py              # Конфигурация (API ключи)
├── database.py            # Работа с базой данных
├── requirements.txt       # Зависимости
├── handlers/              # Обработчики команд и сообщений
│   ├── start_handler.py
│   ├── settings_handler.py
│   ├── video_handler.py
│   └── callback_handler.py
└── services/              # Интеграции с внешними API
    ├── openai_service.py
    ├── recraft_service.py
    └── json2video_service.py
```

## 🌐 Развертывание на сервере

### Развертывание на Railway

Railway автоматически устанавливает зависимости из `requirements.txt` и запускает приложение.

1. Создайте проект в [Railway](https://railway.com/)
2. Подключите GitHub репозиторий
3. Зайдите в панель проекта > Variables
4. Добавьте переменные среды:
   ```
   TELEGRAM_BOT_TOKEN=<your_token>
   OPENAI_API_KEY=<your_key>
   RECRAFT_API_KEY=<your_key>
   JSON2VIDEO_API_KEY=<your_key>
   ```
5. Для производства включите вебхук, установив:
   ```
   WEBHOOK_URL=<your_railway_url>
   ```

Railway автоматически детектит Python приложение и использует `bot.py` как точку входа. Если нужны кастомные настройки, создайте `Procfile` с содержимым:

```
web: python bot.py
```
