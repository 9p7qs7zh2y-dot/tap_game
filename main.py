import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, WebAppInfo
import os
import json
import sqlite3
from datetime import datetime
import requests

# Получаем токен из переменных окружения Render
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8237220454:AAHIs1zJ_h2db7tbPFu7DJWTpp9_PwoLOls")
GAME_URL = "https://asdfsaf-cd54.onrender.com/"

# Создаем бота
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
    print(f"💾 Сохранён игрок {user_id}: {data.get('leaves', 500)}🍃")

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

# Инициализируем базу данных
init_db()

# ===== ОБРАБОТЧИКИ БОТА =====

@bot.message_handler(commands=['start'])
def send_welcome(message):
    welcome_text = """🐨 KOALA × TAP × KOALA

🍃 Факт о коалах:
Коалы спят до 22 часов в день — они настоящие эксперты по энергосбережению.

Что умеет этот бот?
🐨 Кормить эвкалиптом
🐨 Соревноваться
🐨 Прокачивать коалу

✅ Используй команду /play чтобы начать играть!"""
    
    bot.send_message(message.chat.id, welcome_text)

@bot.message_handler(commands=['play'])
def play_game(message):
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton(text="🎮 Открыть игру", web_app=WebAppInfo(url=GAME_URL)))
    bot.send_message(message.chat.id, "Нажми на кнопку, чтобы открыть игру:", reply_markup=keyboard)

@bot.message_handler(commands=['help'])
def send_help(message):
    help_text = """📚 Доступные команды:

/start - приветствие
/play - открыть игру
/help - эта справка

💡 Используй /play чтобы начать игру!"""
    
    bot.send_message(message.chat.id, help_text)

@bot.message_handler(func=lambda message: True)
def handle_other(message):
    response = f"""🍃 Добро пожаловать, {message.from_user.first_name}!

Твоя коала уже ждёт эвкалипт.
Используй команду /play чтобы начать играть!"""
    
    bot.send_message(message.chat.id, response)

# ===== WEBHOOK HANDLER (вместо Flask) =====
def handle_webhook(request_data):
    """Обрабатывает запросы от игры (как Flask, но внутри бота)"""
    try:
        path = request_data.get('path', '/')
        method = request_data.get('method', 'GET')
        body = request_data.get('body', {})
        query = request_data.get('query', {})
        
        print(f"📡 Webhook: {method} {path}")
        
        # API: Сохранение игрока
        if path == '/api/player/save' and method == 'POST':
            user_id = body.get('user_id')
            name = body.get('name', 'Player')
            
            if not user_id:
                return {'status': 'error', 'message': 'No user_id'}, 400
            
            save_all_player_data(user_id, name, body)
            return {'status': 'ok'}, 200
        
        # API: Загрузка игрока
        elif path.startswith('/api/player/') and method == 'GET':
            user_id = int(path.split('/')[-1])
            player_data = load_all_player_data(user_id)
            
            if player_data:
                return player_data, 200
            else:
                return {
                    'leaves': 500, 'stars': 0, 'level': 1, 'exp': 0,
                    'tap_power': 1, 'energy': 100, 'max_energy': 100,
                    'total_taps': 0, 'total_leaves': 0, 'daily_streak': 1,
                    'has_premium': False, 'battles_won': 0
                }, 200
        
        # API: Регистрация игрока
        elif path == '/api/player/register' and method == 'POST':
            user_id = body.get('user_id')
            name = body.get('name', 'Игрок')
            
            if not user_id:
                return {'status': 'error', 'message': 'No user_id'}, 400
            
            existing = load_all_player_data(int(user_id))
            if existing:
                return {'status': 'already_exists'}, 200
            
            save_all_player_data(int(user_id), name, {})
            return {'status': 'ok'}, 200
        
        # Health check
        elif path == '/' or path == '/health':
            return {'status': 'ok'}, 200
        
        else:
            return {'status': 'error', 'message': f'Unknown path: {path}'}, 404
            
    except Exception as e:
        print(f"❌ Webhook error: {e}")
        return {'status': 'error', 'message': str(e)}, 500

# Регистрируем webhook handler
bot.set_webhook_handler(handle_webhook)

# ===== ЗАПУСК =====
if __name__ == "__main__":
    print('🚀 Запуск бота через Webhook...')
    
    # Удаляем старый вебхук
    bot.remove_webhook()
    time.sleep(1)
    
    # Устанавливаем новый вебхук на Render URL
    RENDER_URL = os.environ.get("RENDER_EXTERNAL_URL", GAME_URL.rstrip('/'))
    webhook_url = f"{RENDER_URL}/webhook"
    
    bot.set_webhook(url=webhook_url)
    print(f'✅ Webhook установлен: {webhook_url}')
    print(f'🎮 Игра доступна по адресу: {GAME_URL}')
    
    # Запускаем Flask-совместимый сервер для Render
    from flask import Flask, request as flask_request
    
    app = Flask(__name__)
    
    @app.route('/webhook', methods=['POST'])
    def webhook():
        update = flask_request.get_json()
        if update:
            bot.process_new_updates([telebot.types.Update.de_json(update)])
        return 'OK', 200
    
    @app.route('/', methods=['GET', 'POST', 'HEAD'])
    def catch_all():
        return 'OK', 200
    
    @app.route('/api/player/<path:subpath>', methods=['GET', 'POST'])
    def api_catch_all(subpath):
        return 'OK', 200
    
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
