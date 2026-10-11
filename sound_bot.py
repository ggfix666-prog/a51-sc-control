import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, WebAppInfo, InlineKeyboardMarkup, InlineKeyboardButton
import subprocess, os, json, time, signal, urllib.parse

TOKEN = '8862843776:AAEjax3sBVer7jKKP8DkZPjdygC32f9QDaE'
ADMIN_ID = 6678107119
PULT_URL = 'https://raw.githack.com/ggfix666-prog/a51-sc-control/main/index.html'
SC_DIR = '/sdcard/Music/SoundCloud'
LIB_PATH = '/sdcard/Download/library.json'

bot = telebot.TeleBot(TOKEN)
current_process = None
LIB = []

if os.path.exists(LIB_PATH):
    try:
        with open(LIB_PATH, 'r', encoding='utf-8') as f:
            LIB = json.load(f).get('tracks', [])
    except Exception as e:
        print(f"Ошибка чтения library.json: {e}")

print(f"Треков загружено: {len(LIB)}")

def is_admin(m): return m.from_user.id == ADMIN_ID

@bot.message_handler(func=lambda m: not is_admin(m), content_types=['text'])
def deny(m): bot.reply_to(m, "⛔ Доступ запрещён.")

def play_file(path):
    global current_process
    if current_process and current_process.poll() is None:
        current_process.terminate(); time.sleep(0.3)
    if not os.path.exists(path): return False, "Нет файла"
    try:
        current_process = subprocess.Popen(["mpv","--no-video","--really-quiet", path],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True, None
    except Exception as e: return False, str(e)

def main_kb():
    m = ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
    m.add(KeyboardButton("🎧 SoundCloud", web_app=WebAppInfo(url=PULT_URL)))
    return m

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message,
        f"🎵 A51 Sound — {len(LIB)} треков\n\n"
        "/list — плейлист кнопками\n"
        "/find слово — поиск\n"
        "/stop /pause /resume\n"
        "/volume 50\n"
        "/torch on|off\n"
        "/battery /photo /selfie /location\n\n"
        "Кнопка «🎧 SoundCloud» внизу 👇",
        reply_markup=main_kb())

def build_page(page, items, per=20):
    total = max(1, (len(items)+per-1)//per)
    s = page*per; e = min(s+per, len(items))
    kb = InlineKeyboardMarkup(row_width=1)
    for i in range(s, e):
        t = items[i]
        label = f"🎵 {(t.get('title') or '?')[:45]}"
        if t.get('artist'): label += f"  •  {t['artist'][:20]}"
        kb.add(InlineKeyboardButton(label, callback_data=f"p|{i}"))
    nav = []
    if page > 0: nav.append(InlineKeyboardButton("⬅️", callback_data=f"pg|{page-1}"))
    nav.append(InlineKeyboardButton(f"{page+1}/{total}", callback_data="noop"))
    if e < len(items): nav.append(InlineKeyboardButton("➡️", callback_data=f"pg|{page+1}"))
    kb.row(*nav)
    kb.row(InlineKeyboardButton("⏹ Стоп", callback_data="stop"),
           InlineKeyboardButton("⏸ Пауза", callback_data="pause"),
           InlineKeyboardButton("▶️", callback_data="resume"))
    return kb

@bot.message_handler(commands=['list'])
def list_cmd(message):
    if not LIB: bot.reply_to(message, "📭 Нет треков."); return
    bot.send_message(message.chat.id, f"🎵 Плейлист ({len(LIB)}):", reply_markup=build_page(0, LIB))

@bot.message_handler(commands=['find'])
def find_cmd(message):
    q = message.text.replace('/find','').strip().lower()
    if not q: bot.reply_to(message, "Напиши: /find слово"); return
    found = [(i,t) for i,t in enumerate(LIB) if q in ((t.get('title') or '')+(t.get('artist') or '')).lower()]
    if not found: bot.reply_to(message, "🔍 Не найдено."); return
    kb = InlineKeyboardMarkup(row_width=1)
    for i,t in found[:40]:
        kb.add(InlineKeyboardButton(f"🎵 {(t.get('title') or '?')[:45]}", callback_data=f"p|{i}"))
    bot.send_message(message.chat.id, f"🔍 Найдено: {len(found)}", reply_markup=kb)

@bot.message_handler(commands=['stop'])
def stop_cmd(message):
    global current_process
    if current_process and current_process.poll() is None:
        current_process.terminate(); current_process = None
        bot.reply_to(message, "⏹ Стоп.")
    else: bot.reply_to(message, "Ничего не играет.")

@bot.message_handler(commands=['pause'])
def pause_cmd(message):
    if current_process and current_process.poll() is None:
        try: os.kill(current_process.pid, signal.SIGSTOP); bot.reply_to(message, "⏸ Пауза")
        except Exception as e: bot.reply_to(message, f"Ошибка: {e}")
    else: bot.reply_to(message, "Ничего не играет.")

@bot.message_handler(commands=['resume'])
def resume_cmd(message):
    if current_process and current_process.poll() is None:
        try: os.kill(current_process.pid, signal.SIGCONT); bot.reply_to(message, "▶️ Играю")
        except Exception as e: bot.reply_to(message, f"Ошибка: {e}")
    else: bot.reply_to(message, "Ничего не играет.")

@bot.message_handler(commands=['volume'])
def vol_cmd(message):
    p = message.text.split()
    if len(p) < 2 or not p[1].isdigit():
        bot.reply_to(message, "Напиши: /volume 50"); return
    try:
        subprocess.run(["termux-volume","music",str(int(int(p[1])/100*15))], check=True)
        bot.reply_to(message, f"🔊 {p[1]}%")
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

@bot.message_handler(commands=['battery'])
def batt_cmd(message):
    try:
        r = subprocess.run(["termux-battery-status"], capture_output=True, text=True, check=True)
        d = json.loads(r.stdout)
        bot.reply_to(message, f"🔋 {d.get('percentage')}% • {d.get('status')} • {d.get('temperature')}°C")
    except Exception as e: bot.reply_to(message, f"Ошибка: {e}")

@bot.message_handler(commands=['photo'])
def photo_cmd(message):
    bot.reply_to(message, "📸 Снимаю...")
    p = "/sdcard/Download/a51_photo.jpg"
    try:
        subprocess.run(["termux-camera-photo","-c","0",p], check=True, timeout=15)
        if os.path.exists(p):
            with open(p,'rb') as f: bot.send_photo(message.chat.id, f)
            os.remove(p)
    except Exception as e: bot.reply_to(message, f"Ошибка: {e}")

@bot.message_handler(commands=['selfie'])
def selfie_cmd(message):
    bot.reply_to(message, "🤳 Снимаю...")
    p = "/sdcard/Download/a51_selfie.jpg"
    try:
        subprocess.run(["termux-camera-photo","-c","1",p], check=True, timeout=15)
        if os.path.exists(p):
            with open(p,'rb') as f: bot.send_photo(message.chat.id, f)
            os.remove(p)
    except Exception as e: bot.reply_to(message, f"Ошибка: {e}")

@bot.message_handler(commands=['location'])
def loc_cmd(message):
    bot.reply_to(message, "📍 Ищу GPS...")
    try:
        r = subprocess.run(["termux-location","-p","gps"], capture_output=True, text=True, check=True, timeout=20)
        d = json.loads(r.stdout)
        lat, lon = d.get('latitude'), d.get('longitude')
        bot.reply_to(message, f"📍 {lat}, {lon}\nhttps://maps.google.com/?q={lat},{lon}")
    except Exception as e: bot.reply_to(message, f"Ошибка: {e}")

@bot.callback_query_handler(func=lambda c: True)
def cb(call):
    d = call.data
    if d == "noop": bot.answer_callback_query(call.id); return
    if d == "stop":
        global current_process
        if current_process and current_process.poll() is None:
            current_process.terminate(); current_process = None
        bot.answer_callback_query(call.id, "⏹")
        bot.send_message(call.message.chat.id, "⏹ Остановлено.")
        return
    if d == "pause":
        if current_process and current_process.poll() is None:
            try: os.kill(current_process.pid, signal.SIGSTOP)
            except: pass
        bot.answer_callback_query(call.id, "⏸"); return
    if d == "resume":
        if current_process and current_process.poll() is None:
            try: os.kill(current_process.pid, signal.SIGCONT)
            except: pass
        bot.answer_callback_query(call.id, "▶️"); return
    if d.startswith("pg|"):
        page = int(d.split("|")[1])
        try:
            bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id,
                reply_markup=build_page(page, LIB))
        except: pass
        bot.answer_callback_query(call.id); return
    if d.startswith("p|"):
        i = int(d.split("|")[1])
        if i >= len(LIB): bot.answer_callback_query(call.id, "Не найден"); return
        t = LIB[i]
        path = os.path.join(SC_DIR, t['file'])
        ok, err = play_file(path)
        if ok:
            bot.answer_callback_query(call.id, "▶️")
            bot.send_message(call.message.chat.id, f"▶️ {t.get('title','?')} — {t.get('artist','')}")
        else:
            bot.answer_callback_query(call.id, f"❌ {err}", show_alert=True)
        return

# WEB APP (пульт) — оставляем на всякий
@bot.message_handler(content_types=['web_app_data'])
def webapp(message):
    d = message.web_app_data.data
    try:
        p = d.split("|"); a = p[0]
        if a == "play_file":
            fname = urllib.parse.unquote(p[1])
            path = os.path.join(SC_DIR, fname)
            ok, err = play_file(path)
            bot.send_message(message.chat.id, f"▶️ {fname}" if ok else f"❌ {err}")
        elif a == "stop":
            if current_process and current_process.poll() is None:
                current_process.terminate(); current_process = None
            bot.send_message(message.chat.id, "⏹ Стоп")
        elif a == "volume":
            subprocess.run(["termux-volume","music",str(int(int(p[1])/100*15))])
            bot.send_message(message.chat.id, f"🔊 {p[1]}%")
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ {e}")

print("SoundCloud Bot запущен...")
bot.polling(none_stop=True)
