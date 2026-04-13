import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, WebAppInfo, WebAppQueryResult
import os
from flask import Flask
import threading
import time
import json
import sqlite3
from datetime import datetime

BOT_TOKEN = os.environ.get("BOT_TOKEN", "8237220454:AAHIs1zJ_h2db7tbPFu7DJWTpp9_PwoLOls")
bot = telebot.TeleBot(BOT_TOKEN)

# База данных
def init_db():
    conn = sqlite3.connect('koala_quest.db')
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS players (
        user_id INTEGER PRIMARY KEY,
        name TEXT,
        leaves INTEGER DEFAULT 500,
        stars INTEGER DEFAULT 0,
        level INTEGER DEFAULT 1,
        exp INTEGER DEFAULT 0,
        total_taps INTEGER DEFAULT 0,
        total_leaves INTEGER DEFAULT 0,
        updated_at TIMESTAMP
    )
    ''')
    conn.commit()
    conn.close()
    print("✅ База данных готова")

def save_player(user_id, name, leaves, total_taps):
    conn = sqlite3.connect('koala_quest.db')
    cursor = conn.cursor()
    cursor.execute('''
    INSERT OR REPLACE INTO players (user_id, name, leaves, total_taps, total_leaves, updated_at)
    VALUES (?, ?, ?, ?, ?, ?)
    ''', (user_id, name, leaves, total_taps, leaves, datetime.now()))
    conn.commit()
    conn.close()

def load_player(user_id):
    conn = sqlite3.connect('koala_quest.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM players WHERE user_id = ?', (user_id,))
    row = cursor.fetchone()
    conn.close()
    return row

# Удаляем webhook
try:
    bot.remove_webhook()
    time.sleep(1)
    print("✅ Webhook удалён")
except Exception as e:
    print(f"⚠️ Ошибка: {e}")

# Веб-сервер для Render
web_app = Flask(__name__)

@web_app.route('/')
def health_check():
    return "OK", 200

def run_web():
    web_app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)), threaded=True)

web_thread = threading.Thread(target=run_web, daemon=True)
web_thread.start()
print("🌐 Веб-сервер запущен")

init_db()

# Обработчик данных из игры
@bot.message_handler(content_types=['web_app_data'])
def handle_web_app_data(message):
    try:
        data = json.loads(message.web_app_data.data)
        user_id = message.from_user.id
        user_name = message.from_user.first_name
        action = data.get('action')
        
        print(f"📥 Получены данные от {user_id}: {action}")
        
        # Отвечаем игре (убираем сообщение)
        bot.answer_web_app_query(
            message.web_app_data.query_id,
            WebAppQueryResult(result=json.dumps({"status": "ok"}))
        )
        
        if action == 'tap':
            player = load_player(user_id)
            if player:
                new_leaves = player[2] + data.get('gain', 1)
                new_taps = player[5] + 1
            else:
                new_leaves = 500 + data.get('gain', 1)
                new_taps = 1
            
            save_player(user_id, user_name, new_leaves, new_taps)
            print(f"✅ Сохранено: {user_name} - {new_leaves} листьев")
            
    except Exception as e:
        print(f"⚠️ Ошибка: {e}")

# Команды бота
GAME_URL = "https://asdfsaf-cd54.onrender.com/"

@bot.message_handler(commands=['start'])
def send_welcome(message):
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton(text="🐨 Играть", web_app=WebAppInfo(url=GAME_URL)))
    bot.send_message(message.chat.id, "🐨 Нажми на кнопку, чтобы начать играть!", reply_markup=keyboard)

@bot.message_handler(func=lambda message: True)
def handle_other(message):
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton(text="🐨 Играть", web_app=WebAppInfo(url=GAME_URL)))
    bot.send_message(message.chat.id, f"🍃 Привет, {message.from_user.first_name}! Нажми на кнопку, чтобы тапать!", reply_markup=keyboard)

if __name__ == "__main__":
    print('✅ Бот запущен!')
    while True:
        try:
            bot.infinity_polling(skip_pending=True, timeout=60)
        except Exception as e:
            print(f"⚠️ Ошибка: {e}")
            time.sleep(5)
            print(f"⚠️ Ошибка: {e}")
            print("🔄 Перезапуск через 5 секунд...")
            time.sleep(5)
