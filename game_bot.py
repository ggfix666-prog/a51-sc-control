import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, WebAppInfo
import sqlite3, os, time

TOKEN = '8738305538:AAFSk31fQlGWzNlkuYbVk1aeqsrk_pZp90U'
PULT_URL = 'https://raw.githack.com/ggfix666-prog/a51-sc-control/main/game.html'

bot = telebot.TeleBot(TOKEN)
DB_PATH = '/data/data/com.termux/files/home/players.db'

def init_db():
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS players (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        score INTEGER DEFAULT 0,
        games_played INTEGER DEFAULT 0,
        questions_total INTEGER DEFAULT 0,
        questions_correct INTEGER DEFAULT 0,
        best_time INTEGER DEFAULT 0)''')
    conn.commit(); conn.close()

def get_player(uid, uname=None):
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute('SELECT * FROM players WHERE user_id=?', (uid,))
    row = c.fetchone()
    if not row:
        c.execute('INSERT INTO players (user_id, username) VALUES (?, ?)', (uid, uname or ''))
        conn.commit()
        c.execute('SELECT * FROM players WHERE user_id=?', (uid,))
        row = c.fetchone()
    elif uname and row[1] != uname:
        c.execute('UPDATE players SET username=? WHERE user_id=?', (uname, uid))
        conn.commit()
    conn.close()
    return {'user_id': row[0], 'username': row[1], 'score': row[2],
            'games_played': row[3], 'questions_total': row[4],
            'questions_correct': row[5], 'best_time': row[6]}

def update_player(uid, **kw):
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    for k, v in kw.items():
        c.execute(f'UPDATE players SET {k}=? WHERE user_id=?', (v, uid))
    conn.commit(); conn.close()

def get_top(limit=10):
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute('SELECT username, score, best_time FROM players ORDER BY score DESC LIMIT ?', (limit,))
    rows = c.fetchall(); conn.close(); return rows

def main_kb():
    m = ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
    m.add(KeyboardButton("🎮 Играть", web_app=WebAppInfo(url=PULT_URL)))
    return m

@bot.message_handler(commands=['start'])
def start(msg):
    get_player(msg.from_user.id, msg.from_user.username)
    bot.send_message(msg.chat.id,
        "🎮 <b>hardtekk</b>\n\n"
        "🧠 <b>Викторина</b> — 7 тем, 210 вопросов, до 300 очков.\n"
        "🔢 <b>Математика</b> — 3 уровня, 5 жизней.\n"
        "🔧 <b>Сварка</b> — 2 режима: 2 минуты / до 300 очков.\n\n"
        "📊 /stats — статистика\n"
        "🏆 /top — топ игроков\n\n"
        "Жми <b>«🎮 Играть»</b> внизу 👇",
        parse_mode='HTML', reply_markup=main_kb())

@bot.message_handler(commands=['menu'])
def menu_cmd(msg):
    bot.send_message(msg.chat.id, "Меню 👇", reply_markup=main_kb())

@bot.message_handler(commands=['stats'])
def stats_cmd(msg):
    uid = msg.from_user.id; uname = msg.from_user.username
    p = get_player(uid, uname)
    acc = int(p['questions_correct'] / p['questions_total'] * 100) if p['questions_total'] else 0
    bt = p['best_time'] if p['best_time'] > 0 else '—'
    bot.send_message(msg.chat.id,
        f"📊 <b>Статистика</b>\n\n"
        f"⭐ Очки: {p['score']}\n"
        f"🎮 Игр: {p['games_played']}\n"
        f"🧠 Правильных: {p['questions_correct']}/{p['questions_total']} ({acc}%)\n"
        f"⏱ Лучшее время: {bt}",
        parse_mode='HTML')

@bot.message_handler(commands=['top'])
def top_cmd(msg):
    top = get_top(10)
    if not top:
        bot.send_message(msg.chat.id, "🏆 Пока никто не играл.")
        return
    t = "🏆 <b>Топ игроков:</b>\n\n"
    for i, (un, sc, bt) in enumerate(top, 1):
        medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
        bt_str = f" • ⏱ {bt}с" if bt else ""
        t += f"{medal} @{un or 'игрок'} — {sc} очков{bt_str}\n"
    bot.send_message(msg.chat.id, t, parse_mode='HTML')

# WebApp присылает данные через tg.sendData -> это выглядит как обычное сообщение от пользователя
@bot.message_handler(func=lambda m: m.web_app_data is not None)
def webapp_data(msg):
    raw = msg.web_app_data.data
    parts = raw.split('|')
    cmd = parts[0]
    uid = msg.from_user.id
    uname = msg.from_user.username

    if cmd == 'finish' and len(parts) >= 6:
        # finish|mode|elapsed|score|correct|total
        mode = parts[1]
        elapsed = int(parts[2]) if parts[2] else 0
        total_score = int(parts[3])
        correct = int(parts[4])
        total = int(parts[5])
        p = get_player(uid, uname)
        best = p['best_time']
        if elapsed > 0 and (best == 0 or elapsed < best):
            best = elapsed
        update_player(uid,
            games_played=p['games_played'] + 1,
            best_time=best,
            score=p['score'] + total_score,
            questions_total=p['questions_total'] + total,
            questions_correct=p['questions_correct'] + correct)

        mode_name = {'quiz':'Викторина','math':'Математика','svar':'Сварка'}.get(mode, mode)
        bot.send_message(msg.chat.id,
            f"🏁 <b>{mode_name} завершена!</b>\n\n"
            f"⭐ Очки за игру: {total_score}\n"
            f"✅ Правильных: {correct}/{total}\n"
            f"⏱ Время: {elapsed} сек",
            parse_mode='HTML')

init_db()
print("🎮 Game Bot запущен. URL:", PULT_URL)
while True:
    try:
        bot.polling(none_stop=True, timeout=60, long_polling_timeout=60)
    except KeyboardInterrupt:
        print("Остановлен.")
        break
    except Exception as e:
        print(f"Ошибка: {e}, перезапуск через 5 сек...")
        time.sleep(5)
