import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, WebAppInfo, LabeledPrice
import os
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from flask_socketio import SocketIO, emit, join_room, leave_room
import json
import sqlite3
from datetime import datetime
import time
import eventlet

# Получаем токен из переменных окружения Render
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8237220454:AAHIs1zJ_h2db7tbPFu7DJWTpp9_PwoLOls")
GAME_URL = f"https://koala-bot.onrender.com/?v={int(time.time())}"
RENDER_URL = os.environ.get("RENDER_EXTERNAL_URL", "https://koala-bot.onrender.com".rstrip('/'))

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
        tap_power REAL DEFAULT 1,
        energy REAL DEFAULT 100,
        max_energy REAL DEFAULT 100,
        total_taps INTEGER DEFAULT 0,
        total_leaves INTEGER DEFAULT 0,
        daily_streak INTEGER DEFAULT 1,
        has_premium INTEGER DEFAULT 0,
        battles_won INTEGER DEFAULT 0,
        ref_earnings INTEGER DEFAULT 0,
        last_daily_claim TEXT,
        last_energy_update TEXT,
        updated_at TIMESTAMP
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS tournament_participants (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        name TEXT,
        photo_url TEXT,
        taps INTEGER DEFAULT 0,
        tournament_date TEXT,
        updated_at TIMESTAMP,
        UNIQUE(user_id, tournament_date)
    )
    ''')
    
    # НОВОЕ: таблица достижений
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS achievements (
        user_id INTEGER,
        achievement_id TEXT,
        achieved_at TIMESTAMP,
        PRIMARY KEY (user_id, achievement_id)
    )
    ''')
    
    conn.commit()
    conn.close()
    print("✅ База данных готова (игроки + турниры + достижения)")

def save_all_player_data(user_id, name, data):
    conn = sqlite3.connect('koala_quest.db')
    cursor = conn.cursor()
    cursor.execute('''
    INSERT OR REPLACE INTO players 
    (user_id, name, leaves, stars, level, exp, tap_power, energy, max_energy, 
     total_taps, total_leaves, daily_streak, has_premium, battles_won, ref_earnings, last_daily_claim, last_energy_update, updated_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
        data.get('ref_earnings', 0),
        data.get('last_daily_claim'),
        data.get('last_energy_update'),
        datetime.now()
    ))
    conn.commit()
    conn.close()

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
            'ref_earnings': row[14],
            'last_daily_claim': row[15],
            'last_energy_update': row[16]
        }
    return None

# Инициализируем базу данных
init_db()

# ===== КЛАВИАТУРА =====
def get_main_keyboard():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton(text="🐨 Играть", web_app=WebAppInfo(url=GAME_URL)))
    return keyboard

# ===== РЕФЕРАЛЬНАЯ СИСТЕМА =====
def give_referral_bonus(ref_id, new_user_id, new_user_name):
    try:
        ref_data = load_all_player_data(ref_id)
        if ref_data:
            bonus = 1000
            if ref_data.get('has_premium'):
                bonus = 5000
            
            ref_data['leaves'] = ref_data.get('leaves', 500) + bonus
            ref_data['ref_earnings'] = ref_data.get('ref_earnings', 0) + bonus
            save_all_player_data(ref_id, f"Player_{ref_id}", ref_data)
            
            try:
                bot.send_message(ref_id, f"🎉 {new_user_name} присоединился по твоей ссылке!\n\n💰 Ты получаешь: +{bonus} 🍃")
            except:
                pass
            
            print(f"✅ Реферальный бонус: {ref_id} получил {bonus}🍃 за {new_user_id}")
    except Exception as e:
        print(f"❌ Ошибка в give_referral_bonus: {e}")

# ===== ОБРАБОТЧИКИ БОТА =====

@bot.message_handler(commands=['start'])
def send_welcome(message):
    ref_id = None
    if len(message.text.split()) > 1:
        ref_id = message.text.split()[1]
    
    user_id = message.from_user.id
    user_name = message.from_user.first_name
    
    if ref_id and ref_id != str(user_id):
        try:
            ref_id = int(ref_id)
            give_referral_bonus(ref_id, user_id, user_name)
        except:
            pass
    
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
    bot.send_message(message.chat.id, "📚 Нажми «🐨 Играть» и тапай по коале!", reply_markup=get_main_keyboard())

@bot.message_handler(commands=['invite'])
def invite_command(message):
    user_id = message.from_user.id
    bot_username = bot.get_me().username
    ref_link = f"https://t.me/{bot_username}?start={user_id}"
    
    invite_text = f"""👥 ПРИГЛАСИ ДРУЗЕЙ!

🔗 Твоя персональная ссылка:
{ref_link}

📊 Награды:
• За каждого друга: +1000 🍃
• Если у тебя Премиум: +5000 🍃"""
    
    bot.send_message(message.chat.id, invite_text, reply_markup=get_main_keyboard())

@bot.message_handler(func=lambda message: True)
def handle_other(message):
    bot.send_message(message.chat.id, f"🍃 Нажми на кнопку ниже, чтобы начать тапать!", reply_markup=get_main_keyboard())

# ===== ОБРАБОТЧИКИ ПЛАТЕЖЕЙ =====
@bot.pre_checkout_query_handler(func=lambda query: True)
def checkout(pre_checkout_query):
    bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)

@bot.message_handler(content_types=['successful_payment'])
def got_payment(message):
    user_id = message.from_user.id
    payment_info = message.successful_payment
    invoice_payload = payment_info.invoice_payload
    
    player_data = load_all_player_data(user_id)
    if not player_data:
        player_data = {'leaves': 500, 'stars': 0, 'level': 1, 'has_premium': False}
    
    if invoice_payload.startswith('premium_'):
        player_data['has_premium'] = True
        save_all_player_data(user_id, message.from_user.first_name, player_data)
        bot.send_message(message.chat.id, "✅ Премиум активирован! Двойные награды навсегда!")
    elif invoice_payload.startswith('doubleTap_'):
        bot.send_message(message.chat.id, "✅ Буст «Двойной тап» активирован на 1 час!")
    elif invoice_payload.startswith('autoTap_'):
        bot.send_message(message.chat.id, "✅ Буст «Авто-тап» активирован на 24 часа!")
    elif invoice_payload.startswith('energyBoost_'):
        bot.send_message(message.chat.id, "✅ Буст «Ускоренная энергия» активирован на 12 часов!")

# ===== FLASK + SOCKET.IO =====
app = Flask(__name__)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

# Активные турнирные комнаты
active_tournaments = {}  # {room_id: {participants: {user_id: taps}, start_time, end_time}}

# ===== WebSocket для турниров =====
@socketio.on('join_tournament')
def on_join(data):
    room = data.get('room', 'global_tournament')
    user_id = data.get('user_id')
    user_name = data.get('name', 'Игрок')
    user_photo = data.get('photo')
    
    join_room(room)
    
    if room not in active_tournaments:
        active_tournaments[room] = {
            'participants': {},
            'start_time': time.time(),
            'end_time': time.time() + 60
        }
    
    active_tournaments[room]['participants'][user_id] = {
        'taps': 0,
        'name': user_name,
        'photo': user_photo
    }
    
    # Отправляем всем обновлённый список
    emit('tournament_update', {
        'participants': active_tournaments[room]['participants'],
        'end_time': active_tournaments[room]['end_time']
    }, room=room)
    
    print(f"🏆 {user_name} зашёл в турнир {room}")

@socketio.on('tournament_tap')
def on_tournament_tap(data):
    room = data.get('room', 'global_tournament')
    user_id = data.get('user_id')
    taps = data.get('taps', 0)
    
    if room in active_tournaments and str(user_id) in active_tournaments[room]['participants']:
        active_tournaments[room]['participants'][str(user_id)]['taps'] = taps
        
        # Отправляем обновление всем в комнате
        emit('tournament_update', {
            'participants': active_tournaments[room]['participants'],
            'end_time': active_tournaments[room]['end_time']
        }, room=room)

@socketio.on('leave_tournament')
def on_leave(data):
    room = data.get('room', 'global_tournament')
    user_id = data.get('user_id')
    leave_room(room)
    if room in active_tournaments and str(user_id) in active_tournaments[room]['participants']:
        del active_tournaments[room]['participants'][str(user_id)]

# ===== НОВОЕ: API лидерборда =====
@app.route('/api/leaderboard')
def api_leaderboard():
    try:
        conn = sqlite3.connect('koala_quest.db')
        cursor = conn.cursor()
        cursor.execute('''
        SELECT user_id, name, level, total_leaves, total_taps
        FROM players 
        ORDER BY level DESC, total_leaves DESC
        LIMIT 100
        ''')
        rows = cursor.fetchall()
        conn.close()
        
        leaderboard = []
        for row in rows:
            leaderboard.append({
                'user_id': row[0],
                'name': row[1],
                'level': row[2],
                'total_leaves': row[3],
                'total_taps': row[4]
            })
        
        return jsonify(leaderboard), 200
    except Exception as e:
        print(f"❌ Ошибка лидерборда: {e}")
        return jsonify([]), 200

# ===== НОВОЕ: API достижений =====
@app.route('/api/achievements/<int:user_id>')
def api_achievements(user_id):
    try:
        conn = sqlite3.connect('koala_quest.db')
        cursor = conn.cursor()
        cursor.execute('SELECT achievement_id FROM achievements WHERE user_id = ?', (user_id,))
        rows = cursor.fetchall()
        conn.close()
        return jsonify([r[0] for r in rows]), 200
    except:
        return jsonify([]), 200

@app.route('/api/achievements/save', methods=['POST'])
def api_save_achievement():
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        ach_id = data.get('achievement_id')
        
        conn = sqlite3.connect('koala_quest.db')
        cursor = conn.cursor()
        cursor.execute('INSERT OR IGNORE INTO achievements (user_id, achievement_id, achieved_at) VALUES (?, ?, ?)',
                      (user_id, ach_id, datetime.now()))
        conn.commit()
        conn.close()
        return jsonify({'status': 'ok'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ===== ИГРА =====
@app.route('/')
def serve_game():
    return send_from_directory('static', 'index.html')

@app.route('/static/<path:path>')
def serve_static(path):
    return send_from_directory('static', path)

@app.route('/health', methods=['GET'])
def health():
    return 'OK', 200

# ===== API УВЕДОМЛЕНИЙ ОБ ОПЛАТЕ =====
@app.route('/api/payment_success', methods=['POST'])
def api_payment_success():
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        item = data.get('item')
        amount = data.get('amount')
        
        item_names = {
            'doubleTap': '✨ Двойной тап',
            'autoTap': '🤖 Авто-тап',
            'energyBoost': '⚡ Ускоренная энергия',
            'premium': '🐨 Koala Premium'
        }
        
        item_name = item_names.get(item, item)
        
        if user_id:
            bot.send_message(user_id, f"🎉 Спасибо за покупку!\n🛍️ Товар: {item_name}\n⭐ Потрачено: {amount} Stars")
        
        return jsonify({'status': 'ok'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ===== API СОЗДАНИЯ СЧЕТОВ =====
@app.route('/api/create_invoice', methods=['POST'])
def api_create_invoice():
    try:
        data = request.get_json()
        user_id = int(data.get('user_id'))
        item = data.get('item')
        amount = int(data.get('amount', 1))
        title = data.get('title', 'Покупка')
        description = data.get('description', '')
        
        invoice_payload = f"{item}_{user_id}_{int(time.time())}"
        
        msg = bot.send_invoice(
            chat_id=user_id,
            title=title,
            description=description,
            invoice_payload=invoice_payload,
            provider_token='',
            currency='XTR',
            prices=[LabeledPrice(label=title, amount=amount)]
        )
        
        bot_username = bot.get_me().username
        invoice_link = f"https://t.me/{bot_username}?invoice={msg.message_id}&startapp=pay"
        
        return jsonify({'invoice_link': invoice_link}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ===== API ИГРОКА =====
@app.route('/api/player/save', methods=['POST'])
def api_save_player():
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        name = data.get('name', 'Player')
        save_all_player_data(user_id, name, data)
        return jsonify({'status': 'ok'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/player/<int:user_id>')
def api_load_player(user_id):
    try:
        player_data = load_all_player_data(user_id)
        if player_data:
            return jsonify(player_data), 200
        else:
            return jsonify({
                'leaves': 500, 'stars': 0, 'level': 1, 'exp': 0,
                'tap_power': 1, 'energy': 100, 'max_energy': 100,
                'total_taps': 0, 'total_leaves': 0, 'daily_streak': 1,
                'has_premium': False, 'battles_won': 0, 'ref_earnings': 0
            }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/player/register', methods=['POST', 'GET'])
def api_register_player():
    try:
        if request.is_json:
            data = request.get_json()
            user_id = int(data.get('user_id'))
            name = str(data.get('name', 'Игрок'))
        else:
            user_id = int(request.args.get('user_id'))
            name = str(request.args.get('name', 'Игрок'))
        
        existing = load_all_player_data(user_id)
        if existing:
            return jsonify({'status': 'already_exists'}), 200
        
        default_data = {
            'leaves': 500, 'stars': 0, 'level': 1, 'exp': 0,
            'tap_power': 1, 'energy': 100, 'max_energy': 100,
            'total_taps': 0, 'total_leaves': 0, 'daily_streak': 1,
            'has_premium': False, 'battles_won': 0, 'ref_earnings': 0,
            'last_daily_claim': None, 'last_energy_update': datetime.now().isoformat()
        }
        
        save_all_player_data(user_id, name, default_data)
        return jsonify({'status': 'ok'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ===== API ТУРНИРОВ =====
@app.route('/api/tournament/save', methods=['POST'])
def api_tournament_save():
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        name = data.get('name', 'Игрок')
        photo_url = data.get('photo')
        taps = data.get('taps', 0)
        
        today = datetime.now().strftime('%Y-%m-%d')
        
        conn = sqlite3.connect('koala_quest.db')
        cursor = conn.cursor()
        cursor.execute('''
        INSERT OR REPLACE INTO tournament_participants 
        (user_id, name, photo_url, taps, tournament_date, updated_at)
        VALUES (?, ?, ?, ?, ?, ?)
        ''', (user_id, name, photo_url, taps, today, datetime.now()))
        conn.commit()
        conn.close()
        
        return jsonify({'status': 'ok'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/tournament/participants')
def api_tournament_participants():
    try:
        today = datetime.now().strftime('%Y-%m-%d')
        
        conn = sqlite3.connect('koala_quest.db')
        cursor = conn.cursor()
        cursor.execute('''
        SELECT user_id, name, photo_url, taps 
        FROM tournament_participants 
        WHERE tournament_date = ?
        ORDER BY taps DESC
        LIMIT 100
        ''', (today,))
        
        rows = cursor.fetchall()
        conn.close()
        
        participants = []
        for row in rows:
            participants.append({
                'id': row[0],
                'name': row[1],
                'photo': row[2],
                'taps': row[3]
            })
        
        return jsonify(participants), 200
    except Exception as e:
        return jsonify([]), 200

# Webhook endpoint
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
    print('🚀 Запуск бота через Webhook + Socket.IO...')
    
    bot.remove_webhook()
    webhook_url = f"{RENDER_URL}/webhook"
    bot.set_webhook(url=webhook_url)
    print(f'✅ Webhook установлен: {webhook_url}')
    print(f'🎮 Игра: {GAME_URL}')
    
    port = int(os.environ.get("PORT", 10000))
    socketio.run(app, host='0.0.0.0', port=port, allow_unsafe_werkzeug=True)
