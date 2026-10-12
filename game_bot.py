import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import sqlite3, random, json, os, time, threading
from datetime import datetime

TOKEN = '8738305538:AAFSk31fQlGWzNlkuYbVk1aeqsrk_pZp90U'
bot = telebot.TeleBot(TOKEN)

BASE = '/data/data/com.termux/files/home'
DB_PATH = f'{BASE}/players.db'
Q_FILE = f'{BASE}/questions.json'

DIFF_SCORE = {'easy': 10, 'medium': 20, 'hard': 30}
DIFF_EMOJI = {'easy': '🟢', 'medium': '🟡', 'hard': '🔴'}
DIFF_NAME = {'easy': 'лёгкий', 'medium': 'средний', 'hard': 'сложный'}

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
    conn.commit()
    conn.close()

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
    conn.commit()
    conn.close()

def get_top(limit=10):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT username, score, best_time FROM players ORDER BY score DESC LIMIT ?', (limit,))
    rows = c.fetchall()
    conn.close()
    return rows

def load_questions():
    if os.path.exists(Q_FILE):
        with open(Q_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

# ── СОСТОЯНИЕ ИГР ──
active_solo = {}   # {uid: {...}}
active_duel = {}   # {duel_id: {...}}
waiting_duel = {}  # {uid: duel_id}

def main_menu():
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("🎯 Одиночная игра", callback_data="solo_start"),
        InlineKeyboardButton("⚔️ Дуэль с другом", callback_data="duel_start")
    )
    kb.add(InlineKeyboardButton("🏆 Топ игроков", callback_data="top"))
    kb.add(InlineKeyboardButton("📊 Моя статистика", callback_data="my_stats"))
    return kb

def random_question(qdata):
    """Возвращает случайную тему + случайный вопрос + правильный индекс."""
    theme_key = random.choice(list(qdata.keys()))
    theme = qdata[theme_key]
    q = random.choice(theme['questions'])
    return theme_key, theme['name'], q

@bot.message_handler(commands=['start'])
def start(message):
    get_player(message.from_user.id, message.from_user.username)
    bot.send_message(message.chat.id,
        "🎮 <b>Игровой Бот</b>\n\n"
        "🎯 <b>Одиночная игра</b> — набери 300 очков на время\n"
        "⚔️ <b>Дуэль</b> — сыграй с другом, 20 сек на вопрос\n\n"
        "Выбери режим:",
        parse_mode='HTML', reply_markup=main_menu())

@bot.message_handler(commands=['menu'])
def menu(message):
    bot.send_message(message.chat.id, "Главное меню:", reply_markup=main_menu())

# ── CALLBACKS ──
@bot.callback_query_handler(func=lambda c: True)
def cb(call):
    uid = call.from_user.id
    uname = call.from_user.username
    data = call.data
    chat_id = call.message.chat.id

    # ── СТАРТ ОДИНОЧНОЙ ──
    if data == "solo_start":
        qdata = load_questions()
        if not qdata:
            bot.answer_callback_query(call.id, "Нет вопросов!")
            return
        active_solo[uid] = {
            'score': 0,
            'correct': 0,
            'total': 0,
            'start': time.time(),
            'current': None
        }
        bot.answer_callback_query(call.id, "Погнали!")
        bot.send_message(chat_id,
            "🎯 <b>Одиночная игра</b>\n\n"
            "Цель: набрать 300 очков.\n"
            "🟢 лёгкий = 10 • 🟡 средний = 20 • 🔴 сложный = 30\n\n"
            "Поехали!",
            parse_mode='HTML')
        send_solo_question(chat_id, uid)

    # ── СТАРТ ДУЭЛИ ──
    elif data == "duel_start":
        duel_id = str(int(time.time())) + str(uid)[-4:]
        waiting_duel[uid] = duel_id
        active_duel[duel_id] = {
            'player1': uid,
            'player1_name': uname or f'user{uid}',
            'player2': None,
            'player2_name': None,
            'scores': {uid: 0},
            'current_question': None,
            'current_start': None,
            'answers': {},
            'question_num': 0,
            'chat_id': chat_id
        }
        bot.answer_callback_query(call.id)
        # Приглашение в чат
        bot.send_message(chat_id,
            f"⚔️ <b>Дуэль создана!</b>\n\n"
            f"@{uname or uid} ждёт соперника.\n\n"
            f"Кинь другу ссылку на бота: <b>t.me/MyGameTest7Bot</b>\n"
            f"И пусть он напишет /join {duel_id}",
            parse_mode='HTML')

    # ── JOIN ДУЭЛИ ──
    elif data.startswith("duel_join_"):
        duel_id = data.replace("duel_join_", "")
        if duel_id not in active_duel:
            bot.answer_callback_query(call.id, "Дуэль уже неактуальна")
            return
        d = active_duel[duel_id]
        if d['player2'] is not None:
            bot.answer_callback_query(call.id, "Место занято")
            return
        if uid == d['player1']:
            bot.answer_callback_query(call.id, "Это твоя дуэль")
            return
        d['player2'] = uid
        d['player2_name'] = uname or f'user{uid}'
        d['scores'][uid] = 0
        bot.answer_callback_query(call.id, "В игре!")
        bot.send_message(d['chat_id'],
            f"⚔️ <b>Дуэль началась!</b>\n\n"
            f"@{d['player1_name']} vs @{d['player2_name']}\n\n"
            f"20 секунд на вопрос. Кто больше очков — тот победил!",
            parse_mode='HTML')
        send_duel_question(duel_id)

    # ── ТОП ──
    elif data == "top":
        top = get_top(10)
        if not top:
            bot.send_message(chat_id, "🏆 Пока никто не играл.")
        else:
            t = "🏆 <b>Топ игроков:</b>\n\n"
            for i, (un, sc, bt) in enumerate(top, 1):
                medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
                bt_str = f" • ⏱ {bt}с" if bt else ""
                t += f"{medal} @{un or 'игрок'} — {sc} очков{bt_str}\n"
            bot.send_message(chat_id, t, parse_mode='HTML')
        bot.answer_callback_query(call.id)

    # ── СТАТИСТИКА ──
    elif data == "my_stats":
        p = get_player(uid, uname)
        acc = 0
        if p['questions_total'] > 0:
            acc = int(p['questions_correct'] / p['questions_total'] * 100)
        bt = p['best_time'] if p['best_time'] > 0 else "—"
        bot.send_message(chat_id,
            f"📊 <b>Твоя статистика</b>\n\n"
            f"👤 @{p['username'] or 'игрок'}\n"
            f"⭐ Очки: {p['score']}\n"
            f"🎮 Игр: {p['games_played']}\n"
            f"🧠 Правильных: {p['questions_correct']}/{p['questions_total']} ({acc}%)\n"
            f"⏱ Лучшее время (300 баллов): {bt} сек",
            parse_mode='HTML')
        bot.answer_callback_query(call.id)

    # ── ОТВЕТ В ОДИНОЧНОЙ ──
    elif data.startswith("solo_ans_"):
        if uid not in active_solo:
            bot.answer_callback_query(call.id, "Игра уже закончилась")
            return
        idx = int(data.replace("solo_ans_", ""))
        game = active_solo[uid]
        q = game['current']
        if q is None:
            bot.answer_callback_query(call.id, "Вопрос устарел")
            return
        correct = (idx == q['answer'])
        game['total'] += 1
        if correct:
            game['correct'] += 1
            game['score'] += DIFF_SCORE[q['diff']]
            bot.answer_callback_query(call.id, f"✅ +{DIFF_SCORE[q['diff']]}")
        else:
            bot.answer_callback_query(call.id, f"❌ Правильный: {q['options'][q['answer']]}")
        game['current'] = None
        if game['score'] >= 300:
            finish_solo(chat_id, uid)
        else:
            send_solo_question(chat_id, uid)

    # ── ОТВЕТ В ДУЭЛИ ──
    elif data.startswith("duel_ans_"):
        parts = data.split("_")
        duel_id = parts[2]
        ans_idx = int(parts[3])
        if duel_id not in active_duel:
            bot.answer_callback_query(call.id, "Дуэль закончилась")
            return
        d = active_duel[duel_id]
        if uid not in [d['player1'], d['player2']]:
            bot.answer_callback_query(call.id, "Ты не участник")
            return
        if d['current_question'] is None:
            bot.answer_callback_query(call.id, "Вопрос устарел")
            return
        if uid in d['answers']:
            bot.answer_callback_query(call.id, "Ты уже ответил")
            return
        d['answers'][uid] = ans_idx
        q = d['current_question']
        correct = (ans_idx == q['answer'])
        if correct:
            d['scores'][uid] = d['scores'].get(uid, 0) + DIFF_SCORE[q['diff']]
            bot.answer_callback_query(call.id, f"✅ +{DIFF_SCORE[q['diff']]}")
        else:
            bot.answer_callback_query(call.id, f"❌ Правильный: {q['options'][q['answer']]}")
        # Если оба ответили — следующий вопрос
        if len(d['answers']) == 2:
            finish_duel_question(duel_id)

# ── ОДИНОЧНАЯ ИГРА ──
def send_solo_question(chat_id, uid):
    game = active_solo.get(uid)
    if not game:
        return
    if game['score'] >= 300:
        finish_solo(chat_id, uid)
        return
    qdata = load_questions()
    theme_key, theme_name, q = random_question(qdata)
    game['current'] = q
    emoji = DIFF_EMOJI[q['diff']]
    score = DIFF_SCORE[q['diff']]
    kb = InlineKeyboardMarkup(row_width=1)
    letters = ['A', 'B', 'C', 'D']
    for i, opt in enumerate(q['options']):
        kb.add(InlineKeyboardButton(f"{letters[i]}) {opt}", callback_data=f"solo_ans_{i}"))
    bot.send_message(chat_id,
        f"{emoji} <b>{theme_name}</b> • {DIFF_NAME[q['diff']]} ({score} очков)\n\n"
        f"❓ {q['q']}\n\n"
        f"⭐ Очки: {game['score']}/300",
        parse_mode='HTML', reply_markup=kb)

def finish_solo(chat_id, uid):
    game = active_solo.pop(uid, None)
    if not game:
        return
    elapsed = int(time.time() - game['start'])
    p = get_player(uid)
    best = p['best_time']
    if best == 0 or elapsed < best:
        best = elapsed
    update_player(uid,
        score=p['score'] + game['score'],
        games_played=p['games_played'] + 1,
        questions_total=p['questions_total'] + game['total'],
        questions_correct=p['questions_correct'] + game['correct'],
        best_time=best)
    bot.send_message(chat_id,
        f"🎉 <b>Победа!</b>\n\n"
        f"⭐ Очки: {game['score']}\n"
        f"✅ Правильных: {game['correct']}/{game['total']}\n"
        f"⏱ Время: {elapsed} сек\n\n"
        f"/menu — сыграть ещё",
        parse_mode='HTML')

# ── ДУЭЛЬ ──
def send_duel_question(duel_id):
    d = active_duel.get(duel_id)
    if not d:
        return
    d['question_num'] += 1
    if d['question_num'] > 10:
        finish_duel(duel_id)
        return
    qdata = load_questions()
    _, theme_name, q = random_question(qdata)
    d['current_question'] = q
    d['current_start'] = time.time()
    d['answers'] = {}
    emoji = DIFF_EMOJI[q['diff']]
    score = DIFF_SCORE[q['diff']]
    kb = InlineKeyboardMarkup(row_width=1)
    letters = ['A', 'B', 'C', 'D']
    for i, opt in enumerate(q['options']):
        kb.add(InlineKeyboardButton(f"{letters[i]}) {opt}", callback_data=f"duel_ans_{duel_id}_{i}"))
    # Отправить обоим
    for pid in [d['player1'], d['player2']]:
        if pid:
            bot.send_message(pid,
                f"⚔️ <b>Вопрос {d['question_num']}/10</b>\n"
                f"{emoji} {theme_name} • {DIFF_NAME[q['diff']]} ({score})\n\n"
                f"❓ {q['q']}\n\n"
                f"⏱ У тебя 20 секунд!",
                parse_mode='HTML', reply_markup=kb)
    # Таймер
    threading.Timer(20, duel_timeout, args=[duel_id, d['question_num']]).start()

def duel_timeout(duel_id, qnum):
    d = active_duel.get(duel_id)
    if not d or d['question_num'] != qnum:
        return
    # Если кто-то не ответил — просто считаем, что ответил 0
    finish_duel_question(duel_id)

def finish_duel_question(duel_id):
    d = active_duel.get(duel_id)
    if not d:
        return
    q = d['current_question']
    if q is None:
        return
    # Итог вопроса обоим
    for pid in [d['player1'], d['player2']]:
        if pid:
            pname = "@" + (d['player1_name'] if pid == d['player1'] else d['player2_name'])
            my = d['answers'].get(pid, -1)
            correct = (my == q['answer'])
            text = f"Правильный: {q['options'][q['answer']]}\n"
            text += f"Ты: {'✅ +' + str(DIFF_SCORE[q['diff']]) if correct else '❌'}\n"
            text += f"Счёт: @{d['player1_name']}: {d['scores'].get(d['player1'], 0)} | @{d['player2_name']}: {d['scores'].get(d['player2'], 0)}"
            bot.send_message(pid, text, parse_mode='HTML')
    d['current_question'] = None
    send_duel_question(duel_id)

def finish_duel(duel_id):
    d = active_duel.pop(duel_id, None)
    if not d:
        return
    s1 = d['scores'].get(d['player1'], 0)
    s2 = d['scores'].get(d['player2'], 0) if d['player2'] else 0
    if s1 > s2:
        winner = d['player1_name']
        winner_id = d['player1']
    elif s2 > s1:
        winner = d['player2_name']
        winner_id = d['player2']
    else:
        winner = "ничья"
        winner_id = None
    text = f"🏁 <b>Дуэль завершена!</b>\n\n"
    text += f"@{d['player1_name']}: {s1}\n"
    if d['player2']:
        text += f"@{d['player2_name']}: {s2}\n"
    text += f"\n🏆 Победитель: {winner}"
    bot.send_message(d['chat_id'], text, parse_mode='HTML')
    # Очки победителю
    if winner_id:
        p = get_player(winner_id)
        update_player(winner_id, score=p['score'] + max(s1, s2))

# ── JOIN (текстовая команда) ──
@bot.message_handler(commands=['join'])
def join_cmd(message):
    parts = message.text.split()
    if len(parts) < 2:
        bot.reply_to(message, "Напиши: /join ID_дуэли")
        return
    duel_id = parts[1]
    if duel_id not in active_duel:
        bot.reply_to(message, "Дуэль не найдена или уже началась.")
        return
    d = active_duel[duel_id]
    if d['player2'] is not None:
        bot.reply_to(message, "Место занято.")
        return
    d['player2'] = message.from_user.id
    d['player2_name'] = message.from_user.username or f"user{message.from_user.id}"
    d['scores'][message.from_user.id] = 0
    bot.reply_to(message, "Ты в игре! Начинаем...")
    bot.send_message(d['chat_id'],
        f"⚔️ <b>Дуэль началась!</b>\n\n"
        f"@{d['player1_name']} vs @{d['player2_name']}\n\n"
        f"20 секунд на вопрос. Погнали!",
        parse_mode='HTML')
    send_duel_question(duel_id)

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
