from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash
import google.generativeai as genai
import sqlite3
import bcrypt
import secrets
import smtplib
from email.mime.text import MIMEText
from datetime import datetime, timedelta
import os
import re
import random
import spacy
from nltk import word_tokenize


app = Flask(__name__)
app.secret_key = os.getenv('8f42a6b1d2e9c4f7a9b3e5d8c0f1e2b7', secrets.token_hex(16))  # Use env var or generate new key

# Configure Gemini API
API_KEY = "AIzaSyD_-aBHOjmNnwJAxWXpppexw_PobZF_ZLo"
genai.configure(api_key=API_KEY)
model = genai.GenerativeModel('gemini-1.5-pro')

# Theme-based color schemes
THEME_COLORS = {
    "love": {"bg": "#FFC1CC", "fg": "#800000", "button_bg": "#FF9999", "active_bg": "#FF6666"},
    "action": {"bg": "#1A1A1A", "fg": "#FF4500", "button_bg": "#333333", "active_bg": "#FF6347"},
    "drama": {"bg": "#2F0047", "fg": "#D8BFD8", "button_bg": "#4B0082", "active_bg": "#6A5ACD"},
    "comedy": {"bg": "#FFFF99", "fg": "#FF8C00", "button_bg": "#FFD700", "active_bg": "#FFA500"},
    "tragedy": {"bg": "#333333", "fg": "#A9A9A9", "button_bg": "#555555", "active_bg": "#777777"},
    "adventure": {"bg": "#228B22", "fg": "#F0E68C", "button_bg": "#3CB371", "active_bg": "#2E8B57"},
    "mystery": {"bg": "#191970", "fg": "#E6E6FA", "button_bg": "#483D8B", "active_bg": "#6A5ACD"},
    "family": {"bg": "#87CEEB", "fg": "#2E8B57", "button_bg": "#ADD8E6", "active_bg": "#4682B4"},
    "friendship": {"bg": "#98FB98", "fg": "#006400", "button_bg": "#90EE90", "active_bg": "#32CD32"},
    "default": {"bg": "#333333", "fg": "white", "button_bg": "#555555", "active_bg": "#777777"}
}

MOVIE_DATA = {
    "inception": {"theme": "mystery", "image": "https://image.tmdb.org/t/p/original/qmDpIHrmpJINNiQRCRxSSBlockE.jpg"},
    "the notebook": {"theme": "love", "image": "https://image.tmdb.org/t/p/original/rNxDr15Q7Ky2f7pJUBmP1bh3ods.jpg"},
    "the dark knight": {"theme": "action", "image": "https://image.tmdb.org/t/p/original/qJ2tW6WMUDux911r6m7haRef0WH.jpg"}
}
MOVIE_IMAGES = [data["image"] for data in MOVIE_DATA.values()]  # List of movie images for random selection

# Database setup
def init_db():
    instance_dir = os.path.join(app.instance_path)
    os.makedirs(instance_dir, exist_ok=True)
    db_path = os.path.join(instance_dir, 'users.db')
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (id INTEGER PRIMARY KEY, email TEXT UNIQUE, password TEXT, reset_token TEXT, token_expiry TEXT)''')
    conn.commit()
    conn.close()

try:
    init_db()
except sqlite3.OperationalError as e:
    print(f"Failed to initialize database: {e}")
    exit(1)

# Email configuration
EMAIL_ADDRESS = "your-email@gmail.com"
EMAIL_PASSWORD = "your-app-specific-password"

def send_reset_email(email, token):
    reset_link = url_for('reset_password', token=token, _external=True)
    msg = MIMEText(f"Click this link to reset your password: {reset_link}\nLink expires in 1 hour.")
    msg['Subject'] = 'Password Reset Request'
    msg['From'] = EMAIL_ADDRESS
    msg['To'] = email
    with smtplib.SMTP('smtp.gmail.com', 587) as server:
        server.starttls()
        server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        server.send_message(msg)

# Simulated NLP: Extract sentiment
def extract_sentiment(text):
    text_lower = text.lower()
    if "positive" in text_lower or "great" in text_lower or "excellent" in text_lower:
        return "Positive"
    elif "negative" in text_lower or "poor" in text_lower or "disappointing" in text_lower:
        return "Negative"
    else:
        return "Neutral"

# Simulated NLP: Extract key themes
def extract_themes(text):
    theme_keywords = ["love", "action", "drama", "comedy", "tragedy", "adventure", "mystery", "family", "friendship"]
    words = re.findall(r'\b\w+\b', text.lower())
    themes = [word for word in words if word in theme_keywords]
    return list(set(themes)) if themes else ["Not identified"]

# Add sentiment emoji
def get_sentiment_emoji(sentiment):
    return "😊" if sentiment == "Positive" else "😞" if sentiment == "Negative" else "😐"

# Add emotional response based on popularity
def get_popularity_emotion(popularity):
    if popularity > 4:
        return "🔥 Super Hit!"
    elif popularity == 3:
        return "🎉 Decent Watch!"
    else:
        return "😕 Average Vibes"

# Function to fetch review from Gemini API
def get_movie_review(movie_title):
    try:
        prompt = f"Write a detailed movie review for '{movie_title}'. Include a summary, sentiment (positive/negative), and key themes."
        response = model.generate_content(prompt)
        review_text = response.text

        sentiment = extract_sentiment(review_text)
        themes = extract_themes(review_text)
        popularity = random.randint(1, 5)
        star_rating = "⭐" * popularity + "☆" * (5 - popularity)
        
        movie_info = MOVIE_DATA.get(movie_title.lower(), None)
        if movie_info:
            primary_theme = movie_info["theme"]
            image_url = movie_info["image"]
        else:
            primary_theme = themes[0] if themes and themes[0] != "Not identified" else "default"
            image_url = None
        
        colors = THEME_COLORS.get(primary_theme, THEME_COLORS["default"])
        
        formatted_review = (
            f"🎬 Movie: {movie_title} 🍿\n\n"
            f"{review_text}\n\n"
            f"🌟 Sentiment: {sentiment} {get_sentiment_emoji(sentiment)}\n"
            f"🎭 Key Themes: {', '.join(themes)}\n"
            f"⭐ Popularity: {star_rating} ({popularity}/5) {get_popularity_emotion(popularity)}"
        )
        return {"review": formatted_review, "theme": primary_theme, "colors": colors, "image": image_url}
    except Exception as e:
        return {"review": f"🚫 Error fetching review: {str(e)}", "theme": "default", "colors": THEME_COLORS["default"], "image": None}

# Routes
@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('index.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        if len(password) < 8:
            flash('Password must be at least 8 characters long.')
            return redirect(url_for('signup'))
        
        hashed_pw = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        conn = sqlite3.connect(os.path.join(app.instance_path, 'users.db'))
        c = conn.cursor()
        try:
            c.execute("INSERT INTO users (email, password) VALUES (?, ?)", (email, hashed_pw))
            conn.commit()
            flash('Signup successful! Please log in.')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Email already exists.')
            return redirect(url_for('signup'))
        finally:
            conn.close()
    random_image = random.choice(MOVIE_IMAGES)  # Select random movie poster
    return render_template('signup.html', random_movie_image=random_image)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        conn = sqlite3.connect(os.path.join(app.instance_path, 'users.db'))
        c = conn.cursor()
        c.execute("SELECT id, password FROM users WHERE email = ?", (email,))
        user = c.fetchone()
        conn.close()
        
        if user and bcrypt.checkpw(password.encode('utf-8'), user[1]):
            session['user_id'] = user[0]
            return redirect(url_for('index'))
        else:
            flash('Invalid email or password.')
            return redirect(url_for('login'))
    random_image = random.choice(MOVIE_IMAGES)  # Select random movie poster
    return render_template('login.html', random_movie_image=random_image)

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('login'))

@app.route('/forgot', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form['email']
        conn = sqlite3.connect(os.path.join(app.instance_path, 'users.db'))
        c = conn.cursor()
        c.execute("SELECT id FROM users WHERE email = ?", (email,))
        user = c.fetchone()
        
        if user:
            token = secrets.token_urlsafe(32)
            expiry = datetime.now() + timedelta(hours=1)
            c.execute("UPDATE users SET reset_token = ?, token_expiry = ? WHERE id = ?", 
                      (token, expiry.isoformat(), user[0]))
            conn.commit()
            send_reset_email(email, token)
            flash('Password reset link sent to your email.')
        else:
            flash('Email not found.')
        conn.close()
        return redirect(url_for('forgot_password'))
    return render_template('forgot.html')

@app.route('/reset/<token>', methods=['GET', 'POST'])
def reset_password(token):
    conn = sqlite3.connect(os.path.join(app.instance_path, 'users.db'))
    c = conn.cursor()
    c.execute("SELECT id, token_expiry FROM users WHERE reset_token = ?", (token,))
    user = c.fetchone()
    
    if not user or datetime.fromisoformat(user[1]) < datetime.now():
        flash('Invalid or expired reset link.')
        conn.close()
        return redirect(url_for('forgot_password'))
    
    if request.method == 'POST':
        password = request.form['password']
        if len(password) < 8:
            flash('Password must be at least 8 characters long.')
            return redirect(url_for('reset_password', token=token))
        
        hashed_pw = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        c.execute("UPDATE users SET password = ?, reset_token = NULL, token_expiry = NULL WHERE id = ?", 
                  (hashed_pw, user[0]))
        conn.commit()
        conn.close()
        flash('Password reset successful! Please log in.')
        return redirect(url_for('login'))
    
    conn.close()
    return render_template('reset.html', token=token)

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('dashboard.html')

@app.route('/get_review', methods=['POST'])
def fetch_review():
    if 'user_id' not in session:
        return jsonify({"error": "Please log in first!"})
    movie_title = request.form.get('movie_title', '').strip()
    if not movie_title:
        return jsonify({"error": "Please enter a movie title! 🎥"})
    result = get_movie_review(movie_title)
    return jsonify(result)

if __name__ == '__main__':
    app.run(debug=True)