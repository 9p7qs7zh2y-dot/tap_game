import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, WebAppInfo
import os
from flask import Flask, request, jsonify
import threading
import time
import json
import sqlite3
from datetime import datetime

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
    print(f"💾 Сохранён игрок {user_id}: {data.get('leaves', 500)}🍃")

def load_all_player_data(user_id):
    conn = sqlite3.connect('koala_quest.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM players WHERE user_id = ?', (user_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return {
            'leaves': row[2], 'stars': row[3], 'level': row[4], 'exp': row[5],
            'tap_power': row[6], 'energy': row[7], 'max_energy': row[8],
            'total_taps': row[9], 'total_leaves': row[10], 'daily_streak': row[11],
            'has_premium': bool(row[12]), 'battles_won': row[13]
        }
    return None

# ===== ВЕБ-СЕРВЕР =====
web_app = Flask(__name__)

@web_app.route('/')
def health_check():
    return "OK", 200

@web_app.route('/api/player/save', methods=['POST'])
def api_save():
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        name = data.get('name', 'Player')
        if user_id:
            save_all_player_data(user_id, name, data)
            return jsonify({'status': 'ok'}), 200
        return jsonify({'error': 'No user_id'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@web_app.route('/api/player/<int:user_id>', methods=['GET'])
def api_load(user_id):
    player_data = load_all_player_data(user_id)
    if player_data:
        return jsonify(player_data), 200
    return jsonify({'leaves': 500, 'stars': 0, 'level': 1, 'tap_power': 1, 'energy': 100, 'max_energy': 100}), 200

def run_web():
    web_app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)), threaded=True)

threading.Thread(target=run_web, daemon=True).start()
print("🌐 Веб-сервер запущен")
init_db()

# ===== УДАЛЯЕМ ВЕБХУК =====
try:
    bot.remove_webhook()
    time.sleep(1)
    print("✅ Webhook удалён")
except:
    pass

GAME_URL = "https://asdfsaf-cd54.onrender.com/"

# ===== ОБРАБОТЧИКИ =====
@bot.message_handler(commands=['start'])
def send_welcome(message):
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton(text="🐨 Играть", web_app=WebAppInfo(url=GAME_URL)))
    bot.send_message(message.chat.id, "🐨 Нажми «Играть» и тапай по коале!", reply_markup=keyboard)

# ⭐ ОСНОВНОЙ ОБРАБОТЧИК - БЕЗ ОТПРАВКИ СООБЩЕНИЙ ⭐
@bot.message_handler(content_types=['web_app_data'])
def handle_web_app_data(message):
    try:
        data = json.loads(message.web_app_data.data)
        user_id = message.from_user.id
        user_name = message.from_user.first_name
        
        print(f"📥 Получены данные: {data.get('action')} от {user_name}")
        
        # Только этот ответ - НИКАКИХ bot.send_message!
        bot.answer_web_app_query(message.web_app_data.query_id, json.dumps({"status": "ok"}))
        
        if data.get('action') == 'save_all':
            save_all_player_data(user_id, user_name, data)
        elif data.get('action') == 'load':
            if not load_all_player_data(user_id):
                save_all_player_data(user_id, user_name, {})
                
    except Exception as e:
        print(f"⚠️ Ошибка: {e}")
        try:
            bot.answer_web_app_query(message.web_app_data.query_id, json.dumps({"status": "error"}))
        except:
            pass

@bot.message_handler(func=lambda message: True)
def handle_other(message):
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton(text="🐨 Играть", web_app=WebAppInfo(url=GAME_URL)))
    bot.send_message(message.chat.id, f"🍃 Привет, {message.from_user.first_name}! Нажми «Играть»", reply_markup=keyboard)

if __name__ == "__main__":
    print('✅ Бот запущен!')
    while True:
        try:
            bot.infinity_polling(skip_pending=True, timeout=60)
        except Exception as e:
            print(f"⚠️ Ошибка: {e}")
            time.sleep(5)
