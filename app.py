from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user, UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
import os
import requests
from datetime import datetime, timedelta
import random

# config
app = Flask(__name__, instance_relative_config=True)
app.config.from_mapping(
    SECRET_KEY=os.environ.get("SECRET_KEY", "dev_secret_key"),
    SQLALCHEMY_DATABASE_URI='sqlite:///quiz.db',
    SQLALCHEMY_TRACK_MODIFICATIONS=False
)
# optional: load api keys from instance/config.py
try:
    app.config.from_pyfile('instance/config.py')
except Exception:
    pass

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

# import models here or define below
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)  # login field
    display_name = db.Column(db.String(80), nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    total_score = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, pw):
        self.password_hash = generate_password_hash(pw)

    def check_password(self, pw):
        return check_password_hash(self.password_hash, pw)

class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String(512), nullable=False)
    # store choices as JSON-like (simple approach) OR use separate table.
    # we will use a separate Choice model
    category = db.Column(db.String(80), default='general')

class Choice(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    question_id = db.Column(db.Integer, db.ForeignKey('question.id'), nullable=False)
    text = db.Column(db.String(256), nullable=False)
    is_correct = db.Column(db.Boolean, default=False)

class Attempt(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    score = db.Column(db.Integer, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ---------- ROUTES FOR PAGES ----------
@app.route("/")
def index():
    return render_template("home.html")

@app.route("/register")
def register():
    return render_template("register.html")

@app.route("/login")
def login():
    return render_template("login.html")

@app.route("/quiz")
@login_required
def quiz_page():
    return render_template("quiz.html")

@app.route("/leaderboard")
def leaderboard_page():
    return render_template("leaderboard.html")

# ---------- API ENDPOINTS ----------
# Register
@app.route("/api/register", methods=["POST"])
def api_register():
    data = request.json
    username = data.get("username", "").strip()
    display_name = data.get("display_name", "").strip() or username
    password = data.get("password", "")
    confirm = data.get("confirm", "")
    if not username or not password:
        return jsonify({"error":"username and password required"}), 400
    if password != confirm:
        return jsonify({"error":"passwords do not match"}), 400
    if User.query.filter_by(username=username).first():
        return jsonify({"error":"username already taken"}), 400
    user = User(username=username, display_name=display_name)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    return jsonify({"message":"registered successfully"}), 201

# Login
@app.route("/api/login", methods=["POST"])
def api_login():
    data = request.json
    username = data.get("username","").strip()
    password = data.get("password","")
    user = User.query.filter_by(username=username).first()
    if not user or not user.check_password(password):
        return jsonify({"error":"invalid credentials"}), 401
    login_user(user)
    return jsonify({"message":"logged in", "display_name": user.display_name})

# Logout
@app.route("/api/logout", methods=["POST"])
@login_required
def api_logout():
    logout_user()
    return jsonify({"message":"logged out"})

# Get current user info
@app.route("/api/me")
def api_me():
    if current_user.is_authenticated:
        return jsonify({"username":current_user.username, "display_name":current_user.display_name, "total_score":current_user.total_score})
    return jsonify({"authenticated":False}), 200

# Quiz: get a question (random)
@app.route("/api/question")
@login_required
def api_question():
    qcount = Question.query.count()
    if qcount == 0:
        return jsonify({"error":"no questions available"}), 404
    # pick random question
    q = Question.query.order_by(db.func.random()).first()
    choices = Choice.query.filter_by(question_id=q.id).all()
    choices_data = [{"id":c.id, "text":c.text} for c in choices]
    random.shuffle(choices_data)
    return jsonify({"question":{"id":q.id, "text":q.text}, "choices":choices_data})

# Submit answer
@app.route("/api/submit", methods=["POST"])
@login_required
def api_submit():
    data = request.json
    choice_id = data.get("choice_id")
    qid = data.get("question_id")
    choice = Choice.query.filter_by(id=choice_id, question_id=qid).first()
    if not choice:
        return jsonify({"error":"invalid choice"}), 400
    score = 1 if choice.is_correct else 0
    # update user's total_score
    current_user.total_score = (current_user.total_score or 0) + score
    attempt = Attempt(user_id=current_user.id, score=score)
    db.session.add(attempt)
    db.session.commit()
    return jsonify({"correct": choice.is_correct, "new_total": current_user.total_score})

# Leaderboard
@app.route("/api/leaderboard")
def api_leaderboard():
    users = User.query.order_by(User.total_score.desc(), User.created_at).limit(50).all()
    data = [{"display_name":u.display_name, "username":u.username, "score": u.total_score} for u in users]
    return jsonify(data)

# Weather endpoint - use OpenWeatherMap (user must supply API key in instance/config.py or env OPENWEATHER_API_KEY)
@app.route("/api/weather")
def api_weather():
    city = request.args.get("city", "").strip()
    api_key = app.config.get("OPENWEATHER_API_KEY") or os.environ.get("OPENWEATHER_API_KEY")
    if not city:
        return jsonify({"error":"city required"}), 400
    if not api_key:
        return jsonify({"error":"weather API key not configured. Put OPENWEATHER_API_KEY in env or instance/config.py"}), 500

    # call OpenWeatherMap OneCall or 3-day forecast (we'll use current + daily)
    # We'll call the 3-hour / forecast? For simplicity use "forecast" 3-day approach:
    try:
        # get coordinates by city
        geo_url = f"http://api.openweathermap.org/geo/1.0/direct?q={city}&limit=1&appid={api_key}"
        gresp = requests.get(geo_url).json()
        if not gresp:
            return jsonify({"error":"city not found"}), 404
        lat = gresp[0]['lat']; lon = gresp[0]['lon']
        # One Call 3.0 (if available), else use daily forecast
        onecall = f"https://api.openweathermap.org/data/2.5/onecall?lat={lat}&lon={lon}&exclude=minutely,hourly,alerts&units=metric&appid={api_key}"
        resp = requests.get(onecall)
        j = resp.json()
        daily = j.get("daily", [])[:3]
        result = []
        for d in daily:
            dt = datetime.utcfromtimestamp(d["dt"]) + timedelta(seconds=j.get("timezone_offset",0))
            dayname = dt.strftime("%A")
            result.append({
                "date": dt.strftime("%Y-%m-%d"),
                "day": dayname,
                "temp_day": d["temp"]["day"],
                "temp_night": d["temp"]["night"],
                "weather": d["weather"][0]["description"]
            })
        return jsonify({"city": city, "forecast":result})
    except Exception as e:
        return jsonify({"error":"failed to fetch weather", "detail":str(e)}), 500

# simple API to get total score for current user
@app.route("/api/score")
@login_required
def api_score():
    return jsonify({"total_score": current_user.total_score})

# ---------- helper: create db ----------
@app.cli.command("initdb")
def initdb():
    db.create_all()
    print("Initialized database.")

if __name__ == "__main__":
    # create tables if not exist
    with app.app_context():
        db.create_all()
    app.run(debug=True)
