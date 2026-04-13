import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, WebAppInfo, WebAppQueryResult
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

# ===== СОЗДАЁМ БАЗУ ДАННЫХ =====
def init_db():
    conn = sqlite3.connect('koala_quest.db')
    cursor = conn.cursor()
    
    # Таблица игроков
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
        last_daily_claim TEXT,
        last_energy_update TEXT,
        updated_at TIMESTAMP
    )
    ''')
    
    conn.commit()
    conn.close()
    print("✅ База данных создана")

# Функция сохранения игрока
def save_player(user_id, name, leaves, stars, level, exp, tap_power, energy, max_energy, total_taps, total_leaves, daily_streak, has_premium, last_daily_claim, last_energy_update):
    conn = sqlite3.connect('koala_quest.db')
    cursor = conn.cursor()
    
    cursor.execute('''
    INSERT OR REPLACE INTO players 
    (user_id, name, leaves, stars, level, exp, tap_power, energy, max_energy, total_taps, total_leaves, daily_streak, has_premium, last_daily_claim, last_energy_update, updated_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (user_id, name, leaves, stars, level, exp, tap_power, energy, max_energy, total_taps, total_leaves, daily_streak, 1 if has_premium else 0, last_daily_claim, last_energy_update, datetime.now()))
    
    conn.commit()
    conn.close()
    print(f"💾 Сохранён игрок {user_id}: {leaves} листьев, {total_taps} тапов")

# Функция загрузки игрока
def load_player(user_id):
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
            'last_daily_claim': row[13],
            'last_energy_update': row[14]
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
        bot.answer_web_app_query(
            message.web_app_data.query_id,
            WebAppQueryResult(
                result=json.dumps({"status": "ok"})
            )
        )
        
        if action == 'tap':
            # Загружаем текущие данные игрока
            player = load_player(user_id)
            
            if player:
                # Обновляем существующего игрока
                new_leaves = player['leaves'] + data.get('gain', 1)
                new_total_taps = player['total_taps'] + 1
                new_total_leaves = player['total_leaves'] + data.get('gain', 1)
                new_energy = player['energy'] - 1
                
                save_player(
                    user_id=user_id,
                    name=user_name,
                    leaves=new_leaves,
                    stars=player['stars'],
                    level=player['level'],
                    exp=player['exp'],
                    tap_power=player['tap_power'],
                    energy=max(0, new_energy),
                    max_energy=player['max_energy'],
                    total_taps=new_total_taps,
                    total_leaves=new_total_leaves,
                    daily_streak=player['daily_streak'],
                    has_premium=player['has_premium'],
                    last_daily_claim=player['last_daily_claim'],
                    last_energy_update=datetime.now().isoformat()
                )
            else:
                # Создаём нового игрока
                save_player(
                    user_id=user_id,
                    name=user_name,
                    leaves=500 + data.get('gain', 1),
                    stars=0,
                    level=1,
                    exp=0,
                    tap_power=1,
                    energy=99,
                    max_energy=100,
                    total_taps=1,
                    total_leaves=data.get('gain', 1),
                    daily_streak=1,
                    has_premium=False,
                    last_daily_claim=None,
                    last_energy_update=datetime.now().isoformat()
                )
            
            print(f"✅ Тап сохранён для {user_name}")
            
        elif action == 'load':
            # Игрок запрашивает данные при загрузке игры
            player = load_player(user_id)
            if player:
                # Здесь можно отправить данные обратно в игру
                # Но пока просто логируем
                print(f"📊 Данные загружены для {user_name}: {player['leaves']} листьев")
            
    except Exception as e:
        print(f"⚠️ Ошибка в handle_web_app_data: {e}")

# ===== ОСНОВНОЙ КОД БОТА =====
GAME_URL = "https://asdfsaf-cd54.onrender.com/"

@bot.message_handler(commands=['start'])
def send_welcome(message):
    welcome_text = """🐨 KOALA × TAP × KOALA

🍃 Факт о коалах:
Коалы спят до 22 часов в день!

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
    response = f"""🍃 Привет, {message.from_user.first_name}!

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
