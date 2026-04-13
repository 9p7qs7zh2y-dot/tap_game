import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, WebAppInfo
import os
from flask import Flask
import threading
import time
import json
import sqlite3
from datetime import datetime

# Получаем токен из переменных окружения Render
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8237220454:AAHIs1zJ_h2db7tbPFu7DJWTpp9_PwoLOls")

bot = telebot.TeleBot(BOT_TOKEN)

# ===== БАЗА ДАННЫХ =====
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
        tap_power INTEGER DEFAULT 1,
        energy INTEGER DEFAULT 100,
        max_energy INTEGER DEFAULT 100,
        total_taps INTEGER DEFAULT 0,
        total_leaves INTEGER DEFAULT 0,
        daily_streak INTEGER DEFAULT 1,
        has_premium INTEGER DEFAULT 0,
        battles_won INTEGER DEFAULT 0,
        last_daily_claim TEXT,
        last_energy_update TEXT,
        updated_at TIMESTAMP
    )
    ''')
    conn.commit()
    conn.close()
    print("✅ База данных готова")

def save_all_player_data(user_id, name, data):
    conn = sqlite3.connect('koala_quest.db')
    cursor = conn.cursor()
    cursor.execute('''
    INSERT OR REPLACE INTO players 
    (user_id, name, leaves, stars, level, exp, tap_power, energy, max_energy, 
     total_taps, total_leaves, daily_streak, has_premium, battles_won, last_daily_claim, last_energy_update, updated_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        user_id, name,
        data.get('leaves', 500),
        data.get('stars', 0),
        data.get('level', 1),
        data.get('exp', 0),
        data.get('tap_power', 1),
        data.get('energy', 100),
        data.get('max_energy', 100),
        data.get('total_taps', 0),
        data.get('total_leaves', 0),
        data.get('daily_streak', 1),
        1 if data.get('has_premium', False) else 0,
        data.get('battles_won', 0),
        data.get('last_daily_claim'),
        data.get('last_energy_update'),
        datetime.now()
    ))
    conn.commit()
    conn.close()
    print(f"💾 Сохранён игрок {user_id}: {data.get('leaves', 500)}🍃, {data.get('level', 1)}🏆, {data.get('energy', 100)}⚡")

def load_all_player_data(user_id):
    conn = sqlite3.connect('koala_quest.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM players WHERE user_id = ?', (user_id,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return {
            'leaves': row[2],
            'stars': row[3],
            'level': row[4],
            'exp': row[5],
            'tap_power': row[6],
            'energy': row[7],
            'max_energy': row[8],
            'total_taps': row[9],
            'total_leaves': row[10],
            'daily_streak': row[11],
            'has_premium': bool(row[12]),
            'battles_won': row[13],
            'last_daily_claim': row[14],
            'last_energy_update': row[15]
        }
    return None

# ===== ПРИНУДИТЕЛЬНЫЙ СБРОС WEBHOOK =====
try:
    bot.remove_webhook()
    time.sleep(1)
    print("✅ Webhook удалён")
except Exception as e:
    print(f"⚠️ Ошибка удаления webhook: {e}")

# ===== ВЕБ-СЕРВЕР ДЛЯ RENDER =====
web_app = Flask(__name__)

@web_app.route('/')
def health_check():
    return "OK", 200

@web_app.route('/health')
def health():
    return {"status": "alive"}, 200

def run_web():
    web_app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)), threaded=True)

# Запускаем веб-сервер в отдельном потоке
web_thread = threading.Thread(target=run_web, daemon=True)
web_thread.start()
print("🌐 Веб-сервер запущен")

# Инициализируем базу данных
init_db()

# ===== ОБРАБОТЧИК ДАННЫХ ИЗ МИНИ-ПРИЛОЖЕНИЯ =====
@bot.message_handler(content_types=['web_app_data'])
def handle_web_app_data(message):
    try:
        data = json.loads(message.web_app_data.data)
        user_id = message.from_user.id
        user_name = message.from_user.first_name
        action = data.get('action')
        
        print(f"📥 Получены данные от {user_id}: {action}")
        
        # Отвечаем игре (убираем сообщение)
        try:
            bot.answer_web_app_query(
                message.web_app_data.query_id,
                json.dumps({"status": "ok"})
            )
        except Exception as e:
            print(f"⚠️ Ошибка answer: {e}")
        
        if action == 'save_all':
            # Сохраняем ВСЕ данные игрока
            save_all_player_data(user_id, user_name, data)
            print(f"✅ Сохранены все данные для {user_name}")
            
        elif action == 'load':
            # Загружаем данные игрока
            player_data = load_all_player_data(user_id)
            if player_data:
                # Здесь можно отправить данные обратно в игру
                print(f"📊 Данные загружены для {user_name}: {player_data['leaves']}🍃, уровень {player_data['level']}")
            else:
                print(f"🆕 Новый игрок {user_name}, создаём запись")
                save_all_player_data(user_id, user_name, {})
                
    except Exception as e:
        print(f"⚠️ Ошибка в handle_web_app_data: {e}")

# ===== ОСНОВНОЙ КОД БОТА =====
GAME_URL = "https://asdfsaf-cd54.onrender.com/"

@bot.message_handler(commands=['start'])
def send_welcome(message):
    welcome_text = """🐨 KOALA × TAP × KOALA

🍃 Факт о коалах:
Коалы спят до 22 часов в день — они настоящие эксперты по энергосбережению.

Что умеет этот бот?
🐨 Кормить эвкалиптом
🐨 Соревноваться
🐨 Прокачивать коалу

✅ Нажми на кнопку ниже, чтобы начать играть!
📊 Все твои данные будут сохраняться в облаке!"""

    play_button = KeyboardButton(
        text="🐨 Играть",
        web_app=WebAppInfo(url=GAME_URL)
    )
    
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(play_button)
    
    bot.send_message(message.chat.id, welcome_text, reply_markup=keyboard)

@bot.message_handler(commands=['help'])
def send_help(message):
    help_text = """📚 Доступные команды:

/start - начать игру с коалами
/help - эта справка

💡 Просто нажми «🐨 Играть» и тапай по коале!"""
    
    bot.send_message(message.chat.id, help_text)

@bot.message_handler(func=lambda message: True)
def handle_other(message):
    response = f"""🍃 Добро пожаловать, {message.from_user.first_name}!

Твоя коала уже ждёт эвкалипт.
Нажми на кнопку ниже, чтобы начать тапать!"""
    
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton(
        text="🐨 Играть",
        web_app=WebAppInfo(url=GAME_URL)
    ))
    
    bot.send_message(message.chat.id, response, reply_markup=keyboard)

if __name__ == "__main__":
    print('✅ Бот-коала запущен!')
    print(f'🎮 Игра доступна по адресу: {GAME_URL}')
    
    time.sleep(2)
    
    while True:
        try:
            bot.infinity_polling(skip_pending=True, timeout=60)
        except Exception as e:
            print(f"⚠️ Ошибка: {e}")
            print("🔄 Перезапуск через 5 секунд...")
            time.sleep(5)
