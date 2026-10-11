import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, WebAppInfo, InlineKeyboardMarkup, InlineKeyboardButton
import subprocess
import os
import json
import time
import random
import urllib.parse

TOKEN = '8862843776:AAEjax3sBVer7jKKP8DkZPjdygC32f9QDaE'
ADMIN_ID = 6678107119
PULT_URL = 'https://raw.githack.com/ggfix666-prog/a51-sc-control/main/index.html'
SC_DIR = '/sdcard/Music/SoundCloud'

bot = telebot.TeleBot(TOKEN)
current_process = None
current_file = None
current_started = 0

def is_admin(m): return m.from_user.id == ADMIN_ID

@bot.message_handler(func=lambda m: not is_admin(m), content_types=['text','photo','video','document','voice','audio','video_note','sticker'])
def deny(m): bot.reply_to(m, "⛔ Доступ запрещён.")

def main_kb():
    m = ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
    m.add(KeyboardButton("🎧 SoundCloud", web_app=WebAppInfo(url=PULT_URL)))
    return m

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message,
        "🎵 A51 Sound\n\n"
        "🎧 /playlist — список треков\n"
        "🔊 /volume 50 — громкость\n"
        "⏹ /stop — стоп\n"
        "🔦 /torch on/off\n"
        "📸 /photo /selfie\n"
        "📍 /location /battery\n\n"
        "Кнопка «🎧 SoundCloud» внизу 👇",
        reply_markup=main_kb())

def get_tracks():
    if not os.path.exists(SC_DIR): return []
    return sorted([f for f in os.listdir(SC_DIR) if f.lower().endswith(('.mp3','.m4a','.wav','.ogg','.flac'))])

def play_file(path):
    global current_process, current_file, current_started
    if current_process and current_process.poll() is None:
        current_process.terminate()
        time.sleep(0.3)
    if not os.path.exists(path):
        return False, f"Нет файла: {path}"
    try:
        current_process = subprocess.Popen(
            ["mpv", "--no-video", "--really-quiet", path],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        current_file = path
        current_started = time.time()
        return True, None
    except Exception as e:
        return False, str(e)

@bot.message_handler(commands=['playlist'])
def playlist_menu(message):
    files = get_tracks()
    if not files:
        bot.reply_to(message, "📭 Нет музыки.")
        return
    markup = InlineKeyboardMarkup(row_width=1)
    for i, f in enumerate(files[:50]):
        markup.add(InlineKeyboardButton(f"🎵 {f[:50]}", callback_data=f"pl:{i}"))
    bot.send_message(message.chat.id, f"🎧 Треков: {len(files)}", reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data.startswith("pl:"))
def cb_play(call):
    files = get_tracks()
    idx = int(call.data.split(":")[1])
    if idx >= len(files):
        bot.answer_callback_query(call.id, "Файл пропал"); return
    path = os.path.join(SC_DIR, files[idx])
    ok, err = play_file(path)
    if ok:
        bot.answer_callback_query(call.id, "▶️")
        bot.send_message(call.message.chat.id, f"▶️ {files[idx]}")
    else:
        bot.answer_callback_query(call.id, f"❌ {err}", show_alert=True)

@bot.message_handler(commands=['stop'])
def stop_audio(message):
    global current_process
    if current_process and current_process.poll() is None:
        current_process.terminate(); current_process = None
        bot.reply_to(message, "⏹ Стоп.")
    else:
        bot.reply_to(message, "Ничего не играет.")

@bot.message_handler(commands=['volume'])
def set_volume(message):
    p = message.text.split()
    if len(p) < 2 or not p[1].isdigit():
        bot.reply_to(message, "Напиши: /volume 50"); return
    try:
        subprocess.run(["termux-volume","music",str(int(int(p[1])/100*15))], check=True)
        bot.reply_to(message, f"🔊 {p[1]}%")
    except Exception as e:
        bot.reply_to(message, f"Ошибка: {e}")

@bot.message_handler(commands=['torch'])
def torch_control(message):
    p = message.text.split()
    if len(p) < 2 or p[1].lower() not in ['on','off']:
        bot.reply_to(message, "Напиши: /torch on или /torch off"); return
    try:
        subprocess.run(["termux-torch", p[1].lower()], check=True)
        bot.reply_to(message, f"🔦 {p[1].upper()}")
    except Exception as e:
        bot.reply_to(message, f"Ошибка: {e}")

@bot.message_handler(commands=['battery'])
def battery_status(message):
    try:
        r = subprocess.run(["termux-battery-status"], capture_output=True, text=True, check=True)
        d = json.loads(r.stdout)
        bot.reply_to(message, f"🔋 {d.get('percentage')}% • {d.get('status')} • {d.get('temperature')}°C")
    except Exception as e:
        bot.reply_to(message, f"Ошибка: {e}")

@bot.message_handler(commands=['photo'])
def take_photo(message):
    bot.reply_to(message, "📸 Снимаю...")
    p = "/sdcard/Download/a51_photo.jpg"
    try:
        subprocess.run(["termux-camera-photo","-c","0",p], check=True, timeout=15)
        if os.path.exists(p):
            with open(p,'rb') as f: bot.send_photo(message.chat.id, f)
            os.remove(p)
    except Exception as e:
        bot.reply_to(message, f"Ошибка: {e}")

@bot.message_handler(commands=['selfie'])
def take_selfie(message):
    bot.reply_to(message, "🤳 Снимаю...")
    p = "/sdcard/Download/a51_selfie.jpg"
    try:
        subprocess.run(["termux-camera-photo","-c","1",p], check=True, timeout=15)
        if os.path.exists(p):
            with open(p,'rb') as f: bot.send_photo(message.chat.id, f)
            os.remove(p)
    except Exception as e:
        bot.reply_to(message, f"Ошибка: {e}")

@bot.message_handler(commands=['location'])
def get_location(message):
    bot.reply_to(message, "📍 Ищу GPS...")
    try:
        r = subprocess.run(["termux-location","-p","gps"], capture_output=True, text=True, check=True, timeout=20)
        d = json.loads(r.stdout)
        lat, lon = d.get('latitude'), d.get('longitude')
        bot.reply_to(message, f"📍 {lat}, {lon}\nhttps://maps.google.com/?q={lat},{lon}")
    except Exception as e:
        bot.reply_to(message, f"Ошибка: {e}")

# ---------- WEB APP ----------
@bot.message_handler(content_types=['web_app_data'])
def webapp(message):
    d = message.web_app_data.data
    try:
        p = d.split("|")
        a = p[0]
        
        if a == "play_file":
            raw = p[1] if len(p) > 1 else ""
            fname = urllib.parse.unquote(raw)
            path = os.path.join(SC_DIR, fname)
            print(f"[WEBAPP] play_file -> {path}")
            if not os.path.exists(path):
                bot.send_message(message.chat.id, f"❌ Нет файла: {fname}")
                return
            ok, err = play_file(path)
            if ok:
                bot.send_message(message.chat.id, f"▶️ {fname}")
            else:
                bot.send_message(message.chat.id, f"❌ mpv: {err}")
        
        elif a == "stop":
            global current_process
            if current_process and current_process.poll() is None:
                current_process.terminate(); current_process = None
            bot.send_message(message.chat.id, "⏹ Стоп")
        
        elif a == "volume":
            subprocess.run(["termux-volume","music",str(int(int(p[1])/100*15))])
            bot.send_message(message.chat.id, f"🔊 {p[1]}%")
    
    except Exception as e:
        print(f"[WEBAPP] ERROR: {e}")
        bot.send_message(message.chat.id, f"❌ {e}")

print("SoundCloud Bot запущен...")
bot.polling(none_stop=True)
