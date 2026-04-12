import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, WebAppInfo
import os
from flask import Flask
import threading
import time
import requests
import json

# Получаем токен из переменных окружения Render
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8237220454:AAHIs1zJ_h2db7tbPFu7DJWTpp9_PwoLOls")

bot = telebot.TeleBot(BOT_TOKEN)

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

# ===== ОБРАБОТЧИК ДАННЫХ ИЗ МИНИ-ПРИЛОЖЕНИЯ =====
@bot.message_handler(content_types=['web_app_data'])
def handle_web_app_data(message):
    try:
        data = json.loads(message.web_app_data.data)
        user_id = message.from_user.id
        action = data.get('action')
        
        if action == 'tap':
            requests.post(
                "https://asdfsaf-cd54.onrender.com/api/tap",
                json={"user_id": user_id, "taps_count": data.get('taps_count', 1)},
                headers={"Content-Type": "application/json"}
            )
    except Exception as e:
        print(f"⚠️ Ошибка: {e}")

# ===== ОСНОВНОЙ КОД БОТА =====
# НОВАЯ ССЫЛКА НА RENDER
GAME_URL = "https://asdfsaf-cd54.onrender.com/"

game_button = KeyboardButton(
    text="🐨 Тапать!",
    web_app=WebAppInfo(url=GAME_URL)
)

@bot.message_handler(commands=['start'])
def send_welcome(message):
    welcome_text = """🐨 KOALA × TAP × KOALA

🍃 Факт о коалах:
Коалы спят до 22 часов в день — они настоящие эксперты по энергосбережению.

Что умеет этот бот?
🐨 Кормить эвкалиптом
🐨 Соревноваться
🐨 Прокачивать коалу

Присоединяйся и нажимай «Старт», чтобы начать тапать!

✅ Нажми на кнопку ниже, чтобы играть"""

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
    keyboard.add(game_button)
    
    bot.send_message(message.chat.id, response, reply_markup=keyboard)

if __name__ == "__main__":
    print('✅ Бот-коала запущен!')
    
    # Дополнительная задержка перед запуском polling
    time.sleep(2)
    
    # Запускаем polling с обработкой ошибок
    while True:
        try:
            bot.infinity_polling(skip_pending=True, timeout=60)
        except Exception as e:
            print(f"⚠️ Ошибка: {e}")
            print("🔄 Перезапуск через 5 секунд...")
            time.sleep(5)
