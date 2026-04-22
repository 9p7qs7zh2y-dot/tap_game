import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, WebAppInfo, LabeledPrice
import os
from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import sqlite3
from datetime import datetime
import time

# Получаем токен из переменных окружения Render
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8237220454:AAHIs1zJ_h2db7tbPFu7DJWTpp9_PwoLOls")
# Добавляем параметр версии чтобы избежать кеширования
GAME_URL = f"https://asdfsaf-cd54.onrender.com/?v={int(time.time())}"
RENDER_URL = os.environ.get("RENDER_EXTERNAL_URL", "https://asdfsaf-cd54.onrender.com".rstrip('/'))

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
        ref_earnings INTEGER DEFAULT 0,
        last_daily_claim TEXT,
        last_energy_update TEXT,
        updated_at TIMESTAMP
    )
    ''')
    
    # Таблица для турниров
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
    
    conn.commit()
    conn.close()
    print("✅ База данных готова (игроки + турниры)")

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
    """Начисляет бонус пригласившему"""
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
    help_text = """📚 Доступные команды:

/start - начать игру с коалами
/invite - получить реферальную ссылку
/help - эта справка

💡 Просто нажми «🐨 Играть» и тапай по коале!"""
    
    bot.send_message(message.chat.id, help_text, reply_markup=get_main_keyboard())

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
• Если у тебя Премиум: +5000 🍃

📤 Отправь ссылку другу и получай бонусы!"""
    
    bot.send_message(message.chat.id, invite_text, reply_markup=get_main_keyboard())

@bot.message_handler(func=lambda message: True)
def handle_other(message):
    response = f"""🍃 Добро пожаловать, {message.from_user.first_name}!

Твоя коала уже ждёт эвкалипт.
Нажми на кнопку ниже, чтобы начать тапать!"""
    
    bot.send_message(message.chat.id, response, reply_markup=get_main_keyboard())

# ===== ОБРАБОТЧИКИ ПЛАТЕЖЕЙ TELEGRAM STARS =====
@bot.pre_checkout_query_handler(func=lambda query: True)
def checkout(pre_checkout_query):
    bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)
    print(f"✅ Pre-checkout подтверждён: {pre_checkout_query.id}")

@bot.message_handler(content_types=['successful_payment'])
def got_payment(message):
    user_id = message.from_user.id
    payment_info = message.successful_payment
    invoice_payload = payment_info.invoice_payload
    total_amount = payment_info.total_amount
    currency = payment_info.currency
    
    print(f"💰 Платёж получен: user={user_id}, payload={invoice_payload}, amount={total_amount} {currency}")
    
    player_data = load_all_player_data(user_id)
    if not player_data:
        player_data = {'leaves': 500, 'stars': 0, 'level': 1, 'has_premium': False}
    
    # Обработка разных типов покупок
    if invoice_payload.startswith('premium_'):
        player_data['has_premium'] = True
        save_all_player_data(user_id, message.from_user.first_name, player_data)
        bot.send_message(message.chat.id, "✅ Премиум активирован! Двойные награды навсегда!")
        print(f"✅ Премиум активирован для {user_id}")
    
    elif invoice_payload.startswith('doubleTap_'):
        bot.send_message(message.chat.id, "✅ Буст «Двойной тап» активирован на 1 час!")
        print(f"✅ Двойной тап активирован для {user_id}")
    
    elif invoice_payload.startswith('autoTap_'):
        bot.send_message(message.chat.id, "✅ Буст «Авто-тап» активирован на 24 часа!")
        print(f"✅ Авто-тап активирован для {user_id}")
    
    elif invoice_payload.startswith('energyBoost_'):
        bot.send_message(message.chat.id, "✅ Буст «Ускоренная энергия» активирован на 12 часов!")
        print(f"✅ Ускоренная энергия активирована для {user_id}")
    
    else:
        bot.send_message(message.chat.id, "✅ Спасибо за покупку! Ваш заказ выполнен.")

# ===== FLASK ПРИЛОЖЕНИЕ =====
app = Flask(__name__)
CORS(app)

@app.route('/', methods=['GET', 'HEAD', 'POST'])
def health_check():
    return 'OK', 200, {'Content-Type': 'text/plain'}

@app.route('/health', methods=['GET', 'HEAD', 'POST'])
def health():
    return 'OK', 200, {'Content-Type': 'text/plain'}

# ===== API ДЛЯ УВЕДОМЛЕНИЙ ОБ УСПЕШНОЙ ОПЛАТЕ =====
@app.route('/api/payment_success', methods=['POST', 'OPTIONS'])
def api_payment_success():
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        item = data.get('item')
        amount = data.get('amount')
        
        print(f"📦 Уведомление о покупке: user={user_id}, item={item}, amount={amount}")
        
        item_names = {
            'doubleTap': '✨ Двойной тап',
            'autoTap': '🤖 Авто-тап',
            'energyBoost': '⚡ Ускоренная энергия',
            'premium': '🐨 Koala Premium'
        }
        
        item_name = item_names.get(item, item)
        
        if user_id:
            bot.send_message(
                user_id,
                f"🎉 Спасибо за покупку!\n\n"
                f"🛍️ Товар: {item_name}\n"
                f"⭐ Потрачено: {amount} Stars\n\n"
                f"💫 Приятной игры в Koala Taps!"
            )
            print(f"✅ Уведомление отправлено пользователю {user_id}")
        
        return jsonify({'status': 'ok'}), 200
        
    except Exception as e:
        print(f"❌ Ошибка отправки уведомления: {e}")
        return jsonify({'error': str(e)}), 500

# ===== API ДЛЯ СОЗДАНИЯ СЧЕТОВ (TELEGRAM STARS) =====
@app.route('/api/create_invoice', methods=['POST', 'OPTIONS'])
def api_create_invoice():
    if request.method == 'OPTIONS':
        return '', 200
    
    print("📥 Получен запрос на создание счёта")
    
    try:
        data = request.get_json()
        print(f"📦 Данные запроса: {data}")
        
        user_id = data.get('user_id')
        item = data.get('item')
        amount = data.get('amount', 1)
        title = data.get('title', 'Покупка')
        description = data.get('description', '')
        
        print(f"👤 user_id={user_id}, item={item}, amount={amount}")
        
        if not user_id or not item:
            print("❌ Отсутствует user_id или item")
            return jsonify({'error': 'Missing user_id or item'}), 400
        
        user_id = int(user_id)
        amount = int(amount)
        
        invoice_payload = f"{item}_{user_id}_{int(time.time())}"
        print(f"🔑 Payload: {invoice_payload}")
        
        # Создаём счёт
        print(f"📤 Отправляем send_invoice...")
        bot.send_invoice(
            chat_id=user_id,
            title=title,
            description=description,
            invoice_payload=invoice_payload,
            provider_token='',
            currency='XTR',
            prices=[LabeledPrice(label=title, amount=amount)]
        )
        
        # ✅ ИСПОЛЬЗУЕМ ТОТ ЖЕ PAYLOAD ДЛЯ ССЫЛКИ
        invoice_link = f"https://t.me/invoice/{invoice_payload}"
        
        print(f"📄 Счёт создан: user={user_id}, item={item}, amount={amount} XTR")
        print(f"🔗 Invoice link: {invoice_link}")
        
        return jsonify({'invoice_link': invoice_link}), 200
        
    except Exception as e:
        print(f"❌ Ошибка создания счёта: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/player/save', methods=['POST', 'OPTIONS'])
def api_save_player():
    if request.method == 'OPTIONS':
        return '', 200
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

@app.route('/api/player/<int:user_id>', methods=['GET', 'OPTIONS'])
def api_load_player(user_id):
    if request.method == 'OPTIONS':
        return '', 200
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
                'battles_won': 0,
                'ref_earnings': 0
            }
            print(f"🆕 Новый игрок {user_id}, возвращаем данные по умолчанию")
            return jsonify(default_data), 200
    except Exception as e:
        print(f"API Load Error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/player/register', methods=['POST', 'GET', 'OPTIONS'])
def api_register_player():
    if request.method == 'OPTIONS':
        return '', 200
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
            'has_premium': False, 'battles_won': 0, 'ref_earnings': 0,
            'last_daily_claim': None, 'last_energy_update': datetime.now().isoformat()
        }
        
        save_all_player_data(user_id, name, default_data)
        print(f"✅ Новый игрок {user_id} создан")
        
        return jsonify({'status': 'ok'}), 200
        
    except Exception as e:
        print(f"❌ Ошибка регистрации: {e}")
        return jsonify({'error': str(e)}), 500

# ===== API ТУРНИРОВ =====
@app.route('/api/tournament/save', methods=['POST', 'OPTIONS'])
def api_tournament_save():
    if request.method == 'OPTIONS':
        return '', 200
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        name = data.get('name', 'Игрок')
        photo_url = data.get('photo')
        taps = data.get('taps', 0)
        
        if not user_id:
            return jsonify({'error': 'No user_id'}), 400
        
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
        
        print(f"🏆 Сохранён результат турнира: user={user_id}, taps={taps}")
        return jsonify({'status': 'ok'}), 200
    except Exception as e:
        print(f"❌ Ошибка сохранения турнира: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/tournament/participants', methods=['GET', 'OPTIONS'])
def api_tournament_participants():
    if request.method == 'OPTIONS':
        return '', 200
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
        
        print(f"📤 Отправлено {len(participants)} участников турнира")
        return jsonify(participants), 200
    except Exception as e:
        print(f"❌ Ошибка загрузки турнира: {e}")
        return jsonify([]), 200

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
    
    bot.remove_webhook()
    
    webhook_url = f"{RENDER_URL}/webhook"
    bot.set_webhook(url=webhook_url)
    print(f'✅ Webhook установлен: {webhook_url}')
    print(f'🎮 Игра доступна по адресу: {GAME_URL}')
    
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
