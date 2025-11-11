import os
import sqlite3
import socket
import time
import requests
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, login_user, login_required, logout_user, UserMixin, current_user
from werkzeug.security import generate_password_hash, check_password_hash

from main import name_to_slug, label_sentiment
from scraper import get_reviews
from sentiment import analyze_sentiment
import pandas as pd

DB_PATH = os.path.join(os.path.dirname(__file__), 'app.db')

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key')

login_manager = LoginManager(app)
login_manager.login_view = 'login'

# --- Simple in-memory cache ---
CACHE = {}
CACHE_TTL = 600

def get_cached_reviews(slug: str, max_reviews: int, fetch_fn):
    now = time.time()
    key = (slug, int(max_reviews))
    entry = CACHE.get(key)
    if entry and now - entry['ts'] < CACHE_TTL:
        return entry['data']
    texts = fetch_fn()
    CACHE[key] = {'ts': now, 'data': texts}
    return texts

# --- User model using SQLite ---
class User(UserMixin):
    def __init__(self, id_, username, password_hash):
        self.id = id_
        self.username = username
        self.password_hash = password_hash


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    with conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
            """
        )
        # Seed a public demo URL if none present
        row_url = conn.execute('SELECT value FROM settings WHERE key = ?', ('POWERBI_EMBED_URL',)).fetchone()
        if not row_url or not (row_url['value'] or '').strip():
            conn.execute('INSERT OR REPLACE INTO settings(key, value) VALUES(?, ?)', (
                'POWERBI_EMBED_URL',
                'https://app.powerbi.com/view?r=eyJrIjoiZDYwZmQ3N2UtZmUxZS00ZGRmLWFhYTAtM2QzM2I0M2YzYzQxIiwidCI6IjI2N2QxZDBiLTMwMTItNGUwNy1hN2U3LTY1NzA2N2YyNmM2YSIsImMiOjN9'
            ))
        row = conn.execute('SELECT COUNT(1) AS c FROM users').fetchone()
        if row and row['c'] == 0:
            conn.execute('INSERT INTO users (username, password_hash) VALUES (?, ?)', (
                'demo', generate_password_hash('demo123')
            ))
    conn.close()


@login_manager.user_loader
def load_user(user_id):
    conn = get_db()
    row = conn.execute('SELECT id, username, password_hash FROM users WHERE id = ?', (user_id,)).fetchone()
    conn.close()
    if row:
        return User(row['id'], row['username'], row['password_hash'])
    return None

def get_setting(key: str, default: str = "") -> str:
    conn = get_db()
    row = conn.execute('SELECT value FROM settings WHERE key = ?', (key,)).fetchone()
    conn.close()
    return row['value'] if row and row['value'] is not None else default


def set_setting(key: str, value: str) -> None:
    conn = get_db()
    with conn:
        conn.execute('INSERT INTO settings(key, value) VALUES(?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value', (key, value))
    conn.close()


@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        email = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        if not email or not password:
            flash('Email and password are required.', 'danger')
            return render_template('signup.html')
        pw_hash = generate_password_hash(password)
        try:
            conn = get_db()
            with conn:
                conn.execute('INSERT INTO users (username, password_hash) VALUES (?, ?)', (email, pw_hash))
            flash('Account created. Please sign in.', 'success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('User already exists.', 'danger')
        finally:
            conn.close()
    return render_template('signup.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        conn = get_db()
        row = conn.execute('SELECT id, username, password_hash FROM users WHERE username = ?', (email,)).fetchone()
        conn.close()
        if row and check_password_hash(row['password_hash'], password):
            user = User(row['id'], row['username'], row['password_hash'])
            login_user(user)
            return redirect(url_for('dashboard'))
        flash('Invalid credentials.', 'danger')
    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


@app.route('/demo')
def demo_login():
    conn = get_db()
    row = conn.execute('SELECT id, username, password_hash FROM users WHERE username = ?', ('demo',)).fetchone()
    conn.close()
    if row:
        user = User(row['id'], row['username'], row['password_hash'])
        login_user(user)
        return redirect(url_for('dashboard'))
    flash('Demo user not available.', 'danger')
    return redirect(url_for('login'))


@app.route('/dashboard', methods=['GET', 'POST'])
@login_required
def dashboard():
    results = None
    summary = None
    movie_name = ''
    if request.method == 'POST':
        movie_name = request.form.get('movie', '').strip()
        max_reviews = request.form.get('max_reviews', '').strip()
        try:
            max_reviews = int(max_reviews) if max_reviews else 10
        except ValueError:
            max_reviews = 10
        max_reviews = min(max(max_reviews, 1), 50)
        if not movie_name:
            flash('Please enter a movie name.', 'warning')
        else:
            slug = name_to_slug(movie_name)
            try:
                texts = get_cached_reviews(slug, max_reviews, lambda: get_reviews(slug, max_reviews=max_reviews, delay=1, fast=True, debug=False))
            except Exception as e:
                texts = []
                flash(f'Error fetching reviews: {e}', 'danger')
            if not texts:
                flash('No reviews found. Try adding year, e.g., "Barbie 2023".', 'info')
            else:
                data = []
                for t in texts:
                    score = analyze_sentiment(t)
                    label = label_sentiment(score)
                    data.append({'review': t, 'score': score, 'label': label})
                df = pd.DataFrame(data)
                counts = df['label'].value_counts()
                summary = counts.to_dict()
                # show only first 10 reviews in UI
                results = df.head(10).to_dict(orient='records')
    return render_template('dashboard.html', movie_name=movie_name, results=results, summary=summary)


@app.route('/compare', methods=['GET', 'POST'])
@login_required
def compare():
    left_name = ''
    right_name = ''
    left = { 'summary': None, 'results': None }
    right = { 'summary': None, 'results': None }
    if request.method == 'POST':
        left_name = request.form.get('left_movie', '').strip()
        right_name = request.form.get('right_movie', '').strip()
        max_reviews = request.form.get('max_reviews', '').strip()
        try:
            max_reviews = int(max_reviews) if max_reviews else 10
        except ValueError:
            max_reviews = 10
        max_reviews = min(max(max_reviews, 1), 50)
        if left_name:
            l_slug = name_to_slug(left_name)
            try:
                l_texts = get_cached_reviews(l_slug, max_reviews, lambda: get_reviews(l_slug, max_reviews=max_reviews, delay=1, fast=True, debug=False))
            except Exception:
                l_texts = []
            if l_texts:
                l_data = []
                for t in l_texts:
                    s = analyze_sentiment(t)
                    lbl = label_sentiment(s)
                    l_data.append({'review': t, 'score': s, 'label': lbl})
                l_df = pd.DataFrame(l_data)
                left['summary'] = l_df['label'].value_counts().to_dict()
                left['results'] = l_df.head(10).to_dict(orient='records')
        if right_name:
            r_slug = name_to_slug(right_name)
            try:
                r_texts = get_cached_reviews(r_slug, max_reviews, lambda: get_reviews(r_slug, max_reviews=max_reviews, delay=1, fast=True, debug=False))
            except Exception:
                r_texts = []
            if r_texts:
                r_data = []
                for t in r_texts:
                    s = analyze_sentiment(t)
                    lbl = label_sentiment(s)
                    r_data.append({'review': t, 'score': s, 'label': lbl})
                r_df = pd.DataFrame(r_data)
                right['summary'] = r_df['label'].value_counts().to_dict()
                right['results'] = r_df.head(10).to_dict(orient='records')
    return render_template('compare.html', left_name=left_name, right_name=right_name, left=left, right=right)




if __name__ == '__main__':
    init_db()
    env_port = os.environ.get('PORT')
    if env_port:
        port = int(env_port)
    else:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.bind(('127.0.0.1', 5000))
            port = s.getsockname()[1]
            s.close()
        except OSError:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.bind(('127.0.0.1', 0))
            port = s.getsockname()[1]
            s.close()
    print(f"Running on http://127.0.0.1:{port}")
    app.run(host='127.0.0.1', port=port, debug=False)
