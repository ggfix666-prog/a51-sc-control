import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import sqlite3, random, json, os, time

TOKEN = '8738305538:AAFSk31fQlGWzNlkuYbVk1aeqsrk_pZp90U'
bot = telebot.TeleBot(TOKEN)

DB_PATH = '/data/data/com.termux/files/home/players.db'
QUESTIONS_FILE = '/data/data/com.termux/files/home/questions.json'

# ── БАЗА ДАННЫХ ──
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS players (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        score INTEGER DEFAULT 0,
        games_played INTEGER DEFAULT 0,
        quiz_correct INTEGER DEFAULT 0,
        quiz_total INTEGER DEFAULT 0,
        guess_best INTEGER DEFAULT 999
    )''')
    conn.commit()
    conn.close()

def get_player(user_id, username=None):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT * FROM players WHERE user_id=?', (user_id,))
    row = c.fetchone()
    if not row:
        c.execute('INSERT INTO players (user_id, username) VALUES (?, ?)', (user_id, username or ''))
        conn.commit()
        c.execute('SELECT * FROM players WHERE user_id=?', (user_id,))
        row = c.fetchone()
    elif username and row[1] != username:
        c.execute('UPDATE players SET username=? WHERE user_id=?', (username, user_id))
        conn.commit()
    conn.close()
    return {
        'user_id': row[0], 'username': row[1], 'score': row[2],
        'games_played': row[3], 'quiz_correct': row[4],
        'quiz_total': row[5], 'guess_best': row[6]
    }

def update_player(user_id, **fields):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    for k, v in fields.items():
        c.execute(f'UPDATE players SET {k}=? WHERE user_id=?', (v, user_id))
    conn.commit()
    conn.close()

def get_top(limit=10):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT username, score FROM players ORDER BY score DESC LIMIT ?', (limit,))
    rows = c.fetchall()
    conn.close()
    return rows

# ── ВОПРОСЫ ──
DEFAULT_QUESTIONS = [
    {"q": "Столица Казахстана?", "options": ["Алматы", "Астана", "Шымкент", "Караганда"], "answer": 1},
    {"q": "Сколько планет в Солнечной системе?", "options": ["7", "8", "9", "10"], "answer": 1},
    {"q": "Кто написал «Война и мир»?", "options": ["Пушкин", "Толстой", "Достоевский", "Чехов"], "answer": 1},
    {"q": "Год первого полёта человека в космос?", "options": ["1957", "1961", "1969", "1975"], "answer": 1},
    {"q": "Какой газ преобладает в атмосфере Земли?", "options": ["Кислород", "Азот", "Углекислый", "Водород"], "answer": 1},
    {"q": "Самая длинная река в мире?", "options": ["Амазонка", "Нил", "Янцзы", "Миссисипи"], "answer": 0},
    {"q": "Кто написал «Муму»?", "options": ["Гоголь", "Тургенев", "Пушкин", "Лермонтов"], "answer": 1},
    {"q": "Сколько цветов в радуге?", "options": ["5", "6", "7", "8"], "answer": 2},
    {"q": "Какой океан самый большой?", "options": ["Атлантический", "Индийский", "Тихий", "Северный Ледовитый"], "answer": 2},
    {"q": "Кто изобрёл телефон?", "options": ["Эдисон", "Тесла", "Белл", "Маркони"], "answer": 2},
    {"q": "Какая планета ближе всего к Солнцу?", "options": ["Венера", "Меркурий", "Марс", "Земля"], "answer": 1},
    {"q": "Сколько континентов на Земле?", "options": ["5", "6", "7", "8"], "answer": 2},
    {"q": "Год основания Алматы?", "options": ["1854", "1867", "1921", "1936"], "answer": 0},
    {"q": "Кто написал «Евгений Онегин»?", "options": ["Лермонтов", "Пушкин", "Гоголь", "Некрасов"], "answer": 1},
    {"q": "Какая самая высокая гора в мире?", "options": ["Эльбрус", "Килиманджаро", "Эверест", "Монблан"], "answer": 2},
    {"q": "Сколько сторон у куба?", "options": ["4", "6", "8", "12"], "answer": 1},
    {"q": "Что означает «WWW»?", "options": ["World Wide Web", "Wild West World", "Web World Wide", "Wide Web World"], "answer": 0},
    {"q": "Кто написал «Преступление и наказание»?", "options": ["Толстой", "Достоевский", "Тургенев", "Гоголь"], "answer": 1},
    {"q": "Столица Японии?", "options": ["Пекин", "Сеул", "Токио", "Осака"], "answer": 2},
    {"q": "Какой цвет у неба?", "options": ["Зелёный", "Красный", "Синий", "Фиолетовый"], "answer": 2},
]

def load_questions():
    if os.path.exists(QUESTIONS_FILE):
        try:
            with open(QUESTIONS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except: pass
    return DEFAULT_QUESTIONS

# ── СОСТОЯНИЕ ИГР ──
active_guesses = {}   # {user_id: {"target": 42, "attempts": 0}}
active_quizzes = {}   # {user_id: {"index": 0, "correct": 0, "questions": [...]}}

# ── ГЛАВНОЕ МЕНЮ ──
def main_menu():
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("🔢 Угадай число", callback_data="game_guess"),
        InlineKeyboardButton("🧠 Викторина", callback_data="game_quiz")
    )
    kb.add(InlineKeyboardButton("🏆 Топ игроков", callback_data="top"))
    kb.add(InlineKeyboardButton("📊 Моя статистика", callback_data="my_stats"))
    return kb

@bot.message_handler(commands=['start'])
def start(message):
    get_player(message.from_user.id, message.from_user.username)
    bot.send_message(message.chat.id,
        "🎮 <b>Игровой Бот</b>\n\n"
        "Выбери игру:\n"
        "🔢 <b>Угадай число</b> — угадай число от 1 до 100\n"
        "🧠 <b>Викторина</b> — 10 вопросов на эрудицию\n\n"
        "🏆 Соревнуйся с другими игроками!",
        parse_mode='HTML', reply_markup=main_menu())

@bot.message_handler(commands=['menu'])
def menu(message):
    bot.send_message(message.chat.id, "Главное меню:", reply_markup=main_menu())

# ── КОЛБЭКИ ──
@bot.callback_query_handler(func=lambda c: True)
def cb(call):
    uid = call.from_user.id
    uname = call.from_user.username
    data = call.data

    # ── УГАДАЙ ЧИСЛО ──
    if data == "game_guess":
        target = random.randint(1, 100)
        active_guesses[uid] = {"target": target, "attempts": 0}
        bot.answer_callback_query(call.id, "Игра началась!")
        bot.send_message(call.message.chat.id,
            "🔢 <b>Угадай число!</b>\n\n"
            "Я загадал число от 1 до 100.\n"
            "Напиши число — отвечу «больше», «меньше» или «угадал».\n\n"
            "Чем меньше попыток — тем больше очков!\n\n"
            "Для выхода: /menu",
            parse_mode='HTML')

    # ── ВИКТОРИНА ──
    elif data == "game_quiz":
        qs = load_questions()
        random.shuffle(qs)
        qs = qs[:10]
        active_quizzes[uid] = {"index": 0, "correct": 0, "questions": qs}
        bot.answer_callback_query(call.id, "Начинаем!")
        send_quiz_question(call.message.chat.id, uid)

    # ── ТОП ИГРОКОВ ──
    elif data == "top":
        top = get_top(10)
        if not top:
            bot.send_message(call.message.chat.id, "🏆 Пока никто не играл.")
        else:
            t = "🏆 <b>Топ игроков:</b>\n\n"
            for i, (un, sc) in enumerate(top, 1):
                medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
                t += f"{medal} @{un or 'игрок'} — {sc} очков\n"
            bot.send_message(call.message.chat.id, t, parse_mode='HTML')
        bot.answer_callback_query(call.id)

    # ── СТАТИСТИКА ──
    elif data == "my_stats":
        p = get_player(uid, uname)
        acc = 0
        if p['quiz_total'] > 0:
            acc = int(p['quiz_correct'] / p['quiz_total'] * 100)
        best = p['guess_best'] if p['guess_best'] < 999 else "—"
        bot.send_message(call.message.chat.id,
            f"📊 <b>Твоя статистика</b>\n\n"
            f"👤 @{p['username'] or 'игрок'}\n"
            f"⭐ Очки: {p['score']}\n"
            f"🎮 Игр сыграно: {p['games_played']}\n"
            f"🧠 Викторина: {p['quiz_correct']}/{p['quiz_total']} ({acc}%)\n"
            f"🔢 Лучшее угадывание: {best} попыток",
            parse_mode='HTML')
        bot.answer_callback_query(call.id)

    # ── ОТВЕТ НА ВОПРОС ВИКТОРИНЫ ──
    elif data.startswith("ans_"):
        if uid not in active_quizzes:
            bot.answer_callback_query(call.id, "Игра уже закончилась")
            return
        idx = int(data.split("_")[1])
        quiz = active_quizzes[uid]
        q = quiz['questions'][quiz['index']]
        correct = (idx == q['answer'])
        if correct:
            quiz['correct'] += 1
            bot.answer_callback_query(call.id, "✅ Правильно!")
        else:
            bot.answer_callback_query(call.id, f"❌ Неправильно. Ответ: {q['options'][q['answer']]}")
        quiz['index'] += 1
        if quiz['index'] >= len(quiz['questions']):
            finish_quiz(call.message.chat.id, uid)
        else:
            send_quiz_question(call.message.chat.id, uid)

# ── ВОПРОС ВИКТОРИНЫ ──
def send_quiz_question(chat_id, uid):
    quiz = active_quizzes[uid]
    q = quiz['questions'][quiz['index']]
    kb = InlineKeyboardMarkup(row_width=1)
    for i, opt in enumerate(q['options']):
        kb.add(InlineKeyboardButton(opt, callback_data=f"ans_{i}"))
    bot.send_message(chat_id,
        f"🧠 <b>Вопрос {quiz['index']+1}/10</b>\n\n{q['q']}",
        parse_mode='HTML', reply_markup=kb)

def finish_quiz(chat_id, uid):
    quiz = active_quizzes.pop(uid, None)
    if not quiz: return
    correct = quiz['correct']
    score = correct * 10
    p = get_player(uid)
    update_player(uid,
        score=p['score'] + score,
        games_played=p['games_played'] + 1,
        quiz_correct=p['quiz_correct'] + correct,
        quiz_total=p['quiz_total'] + 10)
    emoji = "🏆" if correct >= 8 else "🎉" if correct >= 5 else "💪"
    bot.send_message(chat_id,
        f"{emoji} <b>Викторина завершена!</b>\n\n"
        f"✅ Правильных: {correct}/10\n"
        f"⭐ Заработано: +{score} очков\n\n"
        f"Хочешь ещё? /menu",
        parse_mode='HTML')

# ── ТЕКСТ (для игры «Угадай число») ──
@bot.message_handler(func=lambda m: m.text and m.text.startswith('/'))
def other_commands(message):
    bot.reply_to(message, "Неизвестная команда. /menu — главное меню.")

@bot.message_handler(func=lambda m: m.from_user.id in active_guesses and m.text and m.text.lstrip('-').isdigit())
def handle_guess(message):
    uid = message.from_user.id
    game = active_guesses.get(uid)
    if not game: return
    try:
        num = int(message.text)
    except: return
    if num < 1 or num > 100:
        bot.reply_to(message, "⚠️ Число от 1 до 100")
        return
    game['attempts'] += 1
    target = game['target']
    if num == target:
        attempts = game['attempts']
        score = max(10, 100 - (attempts - 1) * 5)
        p = get_player(uid, message.from_user.username)
        best = min(p['guess_best'], attempts)
        update_player(uid,
            score=p['score'] + score,
            games_played=p['games_played'] + 1,
            guess_best=best)
        active_guesses.pop(uid, None)
        bot.reply_to(message,
            f"🎉 <b>Угадал!</b>\n\n"
            f"🔢 Число: {target}\n"
            f"🎯 Попыток: {attempts}\n"
            f"⭐ Заработано: +{score} очков\n\n"
            f"Хочешь ещё? /menu",
            parse_mode='HTML')
    elif num < target:
        bot.reply_to(message, f"⬆️ Больше. Попытка {game['attempts']}")
    else:
        bot.reply_to(message, f"⬇️ Меньше. Попытка {game['attempts']}")

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
