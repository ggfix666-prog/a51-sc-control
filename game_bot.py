import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, WebAppInfo, InlineKeyboardMarkup, InlineKeyboardButton
import sqlite3, random, json, os, time

TOKEN = '8738305538:AAFSk31fQlGWzNlkuYbVk1aeqsrk_pZp90U'
PULT_URL = 'https://raw.githack.com/ggfix666-prog/a51-sc-control/main/game.html'
bot = telebot.TeleBot(TOKEN)

DB_PATH = '/data/data/com.termux/files/home/players.db'

# ── БАЗА ──
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS players (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        score INTEGER DEFAULT 0,
        games_played INTEGER DEFAULT 0,
        questions_total INTEGER DEFAULT 0,
        questions_correct INTEGER DEFAULT 0,
        best_time INTEGER DEFAULT 0
    )''')
    conn.commit(); conn.close()

def get_player(uid, uname=None):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
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
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    for k, v in kw.items():
        c.execute(f'UPDATE players SET {k}=? WHERE user_id=?', (v, uid))
    conn.commit(); conn.close()

def get_top(limit=10):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT username, score, best_time FROM players ORDER BY score DESC LIMIT ?', (limit,))
    rows = c.fetchall()
    conn.close(); return rows

def main_kb():
    m = ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
    m.add(KeyboardButton("🎮 Играть", web_app=WebAppInfo(url=PULT_URL)))
    return m

# ── СТАРТ ──
@bot.message_handler(commands=['start'])
def start(message):
    get_player(message.from_user.id, message.from_user.username)
    bot.send_message(message.chat.id,
        "🎮 <b>hardtekk</b>\n\n"
        "🧠 <b>Викторина</b> — набери 300 очков на время.\n"
        "🔢 <b>Математика на время</b> — решай примеры, не теряй жизни.\n\n"
        "Жми <b>«🎮 Играть»</b> внизу 👇",
        parse_mode='HTML', reply_markup=main_kb())

@bot.message_handler(commands=['menu'])
def menu_cmd(message):
    bot.send_message(message.chat.id, "Меню обновлено 👇", reply_markup=main_kb())

# ── ОБРАБОТЧИК КОМАНД ОТ ПУЛЬТА ──
@bot.message_handler(func=lambda m: m.text and m.text.startswith('game:'))
def game_cmd(message):
    raw = message.text[5:]  # без 'game:'
    parts = raw.split('|')
    cmd = parts[0]
    uid = message.from_user.id
    uname = message.from_user.username

    # ── СТАТИСТИКА ──
    if cmd == 'stats':
        p = get_player(uid, uname)
        acc = 0
        if p['questions_total'] > 0:
            acc = int(p['questions_correct'] / p['questions_total'] * 100)
        bt = p['best_time'] if p['best_time'] > 0 else "—"
        bot.send_message(message.chat.id,
            f"📊 <b>Статистика</b>\n\n"
            f"⭐ Очки: {p['score']}\n"
            f"🎮 Игр: {p['games_played']}\n"
            f"🧠 Правильных: {p['questions_correct']}/{p['questions_total']} ({acc}%)\n"
            f"⏱ Лучшее время: {bt} сек",
            parse_mode='HTML')

    # ── ТОП ──
    elif cmd == 'top':
        top = get_top(10)
        if not top:
            bot.send_message(message.chat.id, "🏆 Пока никто не играл.")
        else:
            t = "🏆 <b>Топ игроков:</b>\n\n"
            for i, (un, sc, bt) in enumerate(top, 1):
                medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
                bt_str = f" • ⏱ {bt}с" if bt else ""
                t += f"{medal} @{un or 'игрок'} — {sc} очков{bt_str}\n"
            bot.send_message(message.chat.id, t, parse_mode='HTML')

    # ── ОТВЕТ В ВИКТОРИНЕ ──
    elif cmd == 'answer':
        if len(parts) >= 3:
            diff = parts[1]
            is_correct = parts[2] == '1'
            p = get_player(uid, uname)
            add_score = 0
            if is_correct:
                add_score = 10 if diff == 'easy' else 20 if diff == 'medium' else 30
            update_player(uid,
                questions_total=p['questions_total'] + 1,
                questions_correct=p['questions_correct'] + (1 if is_correct else 0),
                score=p['score'] + add_score)

    # ── ФИНАЛ ВИКТОРИНЫ ──
    elif cmd == 'finish':
        if len(parts) >= 4:
            elapsed = int(parts[1])
            correct = int(parts[2])
            total = int(parts[3])
            p = get_player(uid, uname)
            best = p['best_time']
            if best == 0 or elapsed < best:
                best = elapsed
            update_player(uid,
                games_played=p['games_played'] + 1,
                best_time=best)
            bot.send_message(message.chat.id,
                f"🎉 <b>Победа!</b>\n\n"
                f"⏱ Время: {elapsed} сек\n"
                f"✅ Правильных: {correct}/{total}\n"
                f"⭐ Всего очков: {p['score']}")

    # ── ОТВЕТ В МАТЕМАТИКЕ ──
    elif cmd == 'math_answer':
        if len(parts) >= 3:
            level = parts[1]
            is_correct = parts[2] == '1'
            p = get_player(uid, uname)
            update_player(uid,
                questions_total=p['questions_total'] + 1,
                questions_correct=p['questions_correct'] + (1 if is_correct else 0),
                score=p['score'] + (10 if is_correct else 0))

    # ── ПОТЕРЯ ЖИЗНИ ──
    elif cmd == 'math_life_lost':
        pass  # можно вести отдельный счётчик, если захочешь

    # ── ФИНАЛ МАТЕМАТИКИ ──
    elif cmd == 'math_finish':
        if len(parts) >= 3:
            elapsed = int(parts[1])
            solved = int(parts[2])
            p = get_player(uid, uname)
            best = p['best_time']
            if best == 0 or elapsed < best:
                best = elapsed
            update_player(uid,
                games_played=p['games_played'] + 1,
                best_time=best)
            bot.send_message(message.chat.id,
                f"🏁 <b>Математика завершена!</b>\n\n"
                f"⏱ Время: {elapsed} сек\n"
                f"✅ Решено примеров: {solved}\n"
                f"⭐ Всего очков: {p['score']}",
                parse_mode='HTML')

    # ── ВЫХОД ──
    elif cmd == 'exit':
        pass

# ── ЗАПУСК С ЗАЩИТОЙ ОТ ПАДЕНИЙ ──
init_db()
print("🎮 Game Bot запущен...")
while True:
    try:
        bot.polling(none_stop=True, timeout=60, long_polling_timeout=60)
    except KeyboardInterrupt:
        print("Остановлен вручную.")
        break
    except Exception as e:
        print(f"Ошибка: {e}, перезапуск через 5 сек...")
        time.sleep(5)
