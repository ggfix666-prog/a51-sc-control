import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, WebAppInfo
import sqlite3, os, time

TOKEN = '8738305538:AAFSk31fQlGWzNlkuYbVk1aeqsrk_pZp90U'

# HTML берётся с raw.githack (отдаёт как text/html). Это HTTPS — Telegram WebApp примет.
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
        "Жми <b>«🎮 Играть»</b> внизу 👇",
        parse_mode='HTML', reply_markup=main_kb())

@bot.message_handler(commands=['menu'])
def menu_cmd(msg):
    bot.send_message(msg.chat.id, "Меню 👇", reply_markup=main_kb())

# ── КОМАНДЫ ОТ ПУЛЬТА (статистика / топ / сохранение) ──
@bot.message_handler(func=lambda m: m.text and m.text.startswith('game:'))
def game_cmd(msg):
    raw = msg.text[5:]
    parts = raw.split('|')
    cmd = parts[0]
    uid = msg.from_user.id
    uname = msg.from_user.username

    if cmd == 'stats':
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

    elif cmd == 'top':
        top = get_top(10)
        if not top:
            bot.send_message(msg.chat.id, "🏆 Пока никто не играл.")
        else:
            t = "🏆 <b>Топ игроков:</b>\n\n"
            for i, (un, sc, bt) in enumerate(top, 1):
                medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
                bt_str = f" • ⏱ {bt}с" if bt else ""
                t += f"{medal} @{un or 'игрок'} — {sc} очков{bt_str}\n"
            bot.send_message(msg.chat.id, t, parse_mode='HTML')

    # ответ на вопрос — сохраняем очки и статистику
    elif cmd == 'answer':
        # answer|diff|is_correct|score_delta
        if len(parts) >= 4:
            diff = parts[1]
            ok = parts[2] == '1'
            delta = int(parts[3])
            p = get_player(uid, uname)
            update_player(uid,
                questions_total=p['questions_total'] + 1,
                questions_correct=p['questions_correct'] + (1 if ok else 0),
                score=max(0, p['score'] + delta))

    # финал игры — сохраняем игру, лучшее время, общие очки
    elif cmd == 'finish':
        # finish|mode|elapsed|score
        if len(parts) >= 4:
            mode = parts[1]
            elapsed = int(parts[2]) if parts[2] else 0
            total_score = int(parts[3])
            p = get_player(uid, uname)
            best = p['best_time']
            if elapsed > 0 and (best == 0 or elapsed < best):
                best = elapsed
            update_player(uid,
                games_played=p['games_played'] + 1,
                best_time=best,
                score=total_score)

    elif cmd == 'exit':
        pass

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
