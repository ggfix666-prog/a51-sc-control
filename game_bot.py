import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, WebAppInfo
import sqlite3, os, time, threading
from flask import Flask, request, jsonify, send_from_directory

TOKEN = '8738305538:AAFSk31fQlGWzNlkuYbVk1aeqsrk_pZp90U'
PORT = 5000
HTML_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(HTML_DIR, 'players.db')

# URL туннеля. Меняй содержимое файла webapp_url.txt когда перезапускаешь туннель.
def get_webapp_url():
    try:
        with open(os.path.join(HTML_DIR, 'webapp_url.txt')) as f:
            return f.read().strip()
    except:
        return 'https://example.com'

PULT_URL = get_webapp_url()
bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

@app.after_request
def add_cors(resp):
    resp.headers['Access-Control-Allow-Origin'] = '*'
    resp.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    resp.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    return resp

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

@app.route('/')
@app.route('/game.html')
def serve_game():
    return send_from_directory(HTML_DIR, 'game.html')

@app.route('/api/stats')
def api_stats():
    try: uid = int(request.args.get('uid', 0))
    except: return jsonify({'error': 'bad uid'}), 400
    p = get_player(uid)
    p['accuracy'] = int(p['questions_correct'] / p['questions_total'] * 100) if p['questions_total'] else 0
    return jsonify(p)

@app.route('/api/top')
def api_top():
    return jsonify([{'username': u, 'score': s, 'best_time': b} for u, s, b in get_top(10)])

@app.route('/api/answer', methods=['POST'])
def api_answer():
    d = request.json or {}
    uid = d.get('uid')
    if not uid: return jsonify({'error': 'no uid'}), 400
    p = get_player(uid, d.get('username'))
    diff = d.get('diff', 'easy'); ok = bool(d.get('correct'))
    add = 0
    if ok: add = 10 if diff == 'easy' else 20 if diff == 'medium' else 30
    update_player(uid,
        questions_total=p['questions_total'] + 1,
        questions_correct=p['questions_correct'] + (1 if ok else 0),
        score=p['score'] + add)
    return jsonify({'ok': True})

@app.route('/api/save_game', methods=['POST'])
def api_save_game():
    d = request.json or {}
    uid = d.get('uid')
    if not uid: return jsonify({'error': 'no uid'}), 400
    p = get_player(uid, d.get('username'))
    mode = d.get('mode'); elapsed = int(d.get('elapsed', 0)); add = int(d.get('score', 0))
    best = p['best_time']
    if elapsed > 0 and (best == 0 or elapsed < best): best = elapsed
    if mode in ('quiz', 'svar'):
        update_player(uid,
            games_played=p['games_played'] + 1,
            questions_total=p['questions_total'] + int(d.get('total', 0)),
            questions_correct=p['questions_correct'] + int(d.get('correct', 0)),
            score=p['score'] + add, best_time=best)
    elif mode == 'math':
        update_player(uid,
            games_played=p['games_played'] + 1,
            score=p['score'] + add, best_time=best)
    return jsonify({'ok': True})

def run_flask():
    app.run(host='0.0.0.0', port=PORT, debug=False, use_reloader=False)

def main_kb():
    m = ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
    m.add(KeyboardButton("🎮 Играть", web_app=WebAppInfo(url=PULT_URL)))
    return m

@bot.message_handler(commands=['start'])
def start(msg):
    get_player(msg.from_user.id, msg.from_user.username)
    bot.send_message(msg.chat.id,
        "🎮 <b>hardtekk</b>\n\n"
        "🧠 <b>Викторина</b> — 300 очков на время.\n"
        "🔢 <b>Математика</b> — примеры с жизнями.\n"
        "🔧 <b>Сварка</b> — вопросы по профессии.\n\n"
        "Жми <b>«🎮 Играть»</b> внизу 👇",
        parse_mode='HTML', reply_markup=main_kb())

@bot.message_handler(commands=['menu'])
def menu_cmd(msg):
    bot.send_message(msg.chat.id, "Меню 👇", reply_markup=main_kb())

if __name__ == '__main__':
    init_db()
    threading.Thread(target=run_flask, daemon=True).start()
    print(f"🎮 Bot started. WebApp URL: {PULT_URL}")
    print(f"📡 API: http://0.0.0.0:{PORT}")
    while True:
        try:
            bot.polling(none_stop=True, timeout=60, long_polling_timeout=60)
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Error: {e}, restart in 5s...")
            time.sleep(5)
