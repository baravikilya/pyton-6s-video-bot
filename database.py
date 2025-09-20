import sys
import os

# Добавляем родительскую директорию в путь поиска модулей
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import sqlite3
import os

# Путь к файлу базы данных
DB_PATH = "users.db"

def init_db():
    """Инициализация базы данных и создание таблицы пользователей"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Создание таблицы пользователей
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER UNIQUE NOT NULL,
            language TEXT,
            mode TEXT
        )
    ''')
    
    conn.commit()
    conn.close()

def get_user(telegram_id):
    """Получение данных пользователя по telegram_id"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM users WHERE telegram_id = ?', (telegram_id,))
    user = cursor.fetchone()
    
    conn.close()
    return user

def create_user(telegram_id):
    """Создание нового пользователя"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT OR IGNORE INTO users (telegram_id) VALUES (?)
    ''', (telegram_id,))
    
    conn.commit()
    conn.close()

def update_user_settings(telegram_id, language=None, mode=None):
    """Обновление настроек пользователя"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    if language and mode:
        cursor.execute('''
            UPDATE users SET language = ?, mode = ? WHERE telegram_id = ?
        ''', (language, mode, telegram_id))
    elif language:
        cursor.execute('''
            UPDATE users SET language = ? WHERE telegram_id = ?
        ''', (language, telegram_id))
    elif mode:
        cursor.execute('''
            UPDATE users SET mode = ? WHERE telegram_id = ?
        ''', (mode, telegram_id))
    
    conn.commit()
    conn.close()