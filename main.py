import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, WebAppInfo
import os
from flask import Flask, request, jsonify
import json
import sqlite3
from datetime import datetime

# Получаем токен из переменных окружения Render
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8237220454:AAHIs1zJ_h2db7tbPFu7DJWTpp9_PwoLOls")
GAME_URL = "https://asdfsaf-cd54.onrender.com/"
RENDER_URL = os.environ.get("RENDER_EXTERNAL_URL", GAME_URL.rstrip('/'))

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

# ===== КЛАВИАТУРА =====
def get_main_keyboard():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton(text="🐨 Играть", web_app=WebAppInfo(url=GAME_URL)))
    return keyboard

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

Присоединяйся и нажимай «Играть», чтобы начать тапать!"""
    
    bot.send_message(message.chat.id, welcome_text, reply_markup=get_main_keyboard())

@bot.message_handler(commands=['help'])
def send_help(message):
    help_text = """📚 Доступные команды:

/start - начать игру с коалами
/help - эта справка

💡 Просто нажми «🐨 Играть» и тапай по коале!"""
    
    bot.send_message(message.chat.id, help_text, reply_markup=get_main_keyboard())

@bot.message_handler(func=lambda message: True)
def handle_other(message):
    response = f"""🍃 Добро пожаловать, {message.from_user.first_name}!

Твоя коала уже ждёт эвкалипт.
Нажми на кнопку ниже, чтобы начать тапать!"""
    
    bot.send_message(message.chat.id, response, reply_markup=get_main_keyboard())

# ===== FLASK ПРИЛОЖЕНИЕ =====
app = Flask(__name__)

@app.route('/', methods=['GET', 'HEAD'])
def health_check():
    return "OK", 200

@app.route('/health', methods=['GET', 'HEAD'])
def health():
    return {"status": "alive"}, 200

@app.route('/api/player/save', methods=['POST'])
def api_save_player():
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        name = data.get('name', 'Player')
        
        print(f"📥 API сохранение: user_id={user_id}, leaves={data.get('leaves')}")
        
        if not user_id:
            return jsonify({'error': 'No user_id'}), 400
        
        save_all_player_data(user_id, name, data)
        print(f"✅ API сохранил игрока {user_id}")
        return jsonify({'status': 'ok'}), 200
    except Exception as e:
        print(f"API Error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/player/<int:user_id>', methods=['GET'])
def api_load_player(user_id):
    try:
        player_data = load_all_player_data(user_id)
        
        if player_data:
            print(f"📤 API загрузил игрока {user_id}: {player_data['leaves']}🍃")
            return jsonify(player_data), 200
        else:
            default_data = {
                'leaves': 500,
                'stars': 0,
                'level': 1,
                'exp': 0,
                'tap_power': 1,
                'energy': 100,
                'max_energy': 100,
                'total_taps': 0,
                'total_leaves': 0,
                'daily_streak': 1,
                'has_premium': False,
                'battles_won': 0
            }
            print(f"🆕 Новый игрок {user_id}, возвращаем данные по умолчанию")
            return jsonify(default_data), 200
    except Exception as e:
        print(f"API Load Error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/player/register', methods=['POST', 'GET'])
def api_register_player():
    try:
        if request.is_json:
            data = request.get_json()
            user_id = data.get('user_id')
            name = data.get('name', 'Игрок')
            print(f"📝 POST регистрация: {user_id} ({name})")
        else:
            user_id = request.args.get('user_id')
            name = request.args.get('name', 'Игрок')
            print(f"📝 GET регистрация: {user_id} ({name})")
        
        if not user_id:
            print("❌ Ошибка: нет user_id")
            return jsonify({'error': 'No user_id'}), 400
        
        user_id = int(user_id)
        name = str(name)
        
        print(f"✅ Регистрация игрока: {user_id} ({name})")
        
        existing = load_all_player_data(user_id)
        if existing:
            print(f"ℹ️ Игрок {user_id} уже существует")
            return jsonify({'status': 'already_exists'}), 200
        
        default_data = {
            'leaves': 500, 'stars': 0, 'level': 1, 'exp': 0,
            'tap_power': 1, 'energy': 100, 'max_energy': 100,
            'total_taps': 0, 'total_leaves': 0, 'daily_streak': 1,
            'has_premium': False, 'battles_won': 0,
            'last_daily_claim': None, 'last_energy_update': datetime.now().isoformat()
        }
        
        save_all_player_data(user_id, name, default_data)
        print(f"✅ Новый игрок {user_id} создан")
        
        return jsonify({'status': 'ok'}), 200
        
    except Exception as e:
        print(f"❌ Ошибка регистрации: {e}")
        return jsonify({'error': str(e)}), 500

# Webhook endpoint для Telegram
@app.route('/webhook', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return 'OK', 200
    return 'Bad Request', 400

# ===== ЗАПУСК =====
if __name__ == "__main__":
    print('🚀 Запуск бота через Webhook...')
    
    # Удаляем старый вебхук
    bot.remove_webhook()
    
    # Устанавливаем новый вебхук
    webhook_url = f"{RENDER_URL}/webhook"
    bot.set_webhook(url=webhook_url)
    print(f'✅ Webhook установлен: {webhook_url}')
    print(f'🎮 Игра доступна по адресу: {GAME_URL}')
    
    # Запускаем Flask сервер
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
