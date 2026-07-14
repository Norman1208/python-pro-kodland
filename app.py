from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user, UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
import os
import requests
from datetime import datetime, timedelta
import random

# --- Config ---
app = Flask(__name__, instance_relative_config=True)
app.config.from_mapping(
    SECRET_KEY=os.environ.get("SECRET_KEY", "dev_secret_key_change_in_prod"),
    SQLALCHEMY_DATABASE_URI='sqlite:///quiz.db',
    SQLALCHEMY_TRACK_MODIFICATIONS=False
)
try:
    app.config.from_pyfile('instance/config.py')
except Exception:
    pass

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

# --- Models ---
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    display_name = db.Column(db.String(80), nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    best_score = db.Column(db.Float, default=0.0)   # skor terbaik dalam %
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __init__(self, username: str, display_name: str, **kwargs):
        super().__init__(**kwargs)
        self.username = username
        self.display_name = display_name

    def set_password(self, pw):
        self.password_hash = generate_password_hash(pw)

    def check_password(self, pw):
        return check_password_hash(self.password_hash, pw)

class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String(512), nullable=False)
    category = db.Column(db.String(80), default='general')
    choices = db.relationship('Choice', backref='question', lazy=True)

class Choice(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    question_id = db.Column(db.Integer, db.ForeignKey('question.id'), nullable=False)
    text = db.Column(db.String(256), nullable=False)
    is_correct = db.Column(db.Boolean, default=False)

class Attempt(db.Model):
    """Satu percobaan ujian (5 soal)."""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    total_questions = db.Column(db.Integer, default=5)
    correct_answers = db.Column(db.Integer, default=0)
    score_pct = db.Column(db.Float, default=0.0)   # 0–100
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    def __init__(self, user_id: int, total_questions: int = 5,
                 correct_answers: int = 0, score_pct: float = 0.0, **kwargs):
        super().__init__(**kwargs)
        self.user_id = user_id
        self.total_questions = total_questions
        self.correct_answers = correct_answers
        self.score_pct = score_pct

class ImageDetection(db.Model):
    """Hasil deteksi gambar yang disimpan ke DB."""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    predicted_class = db.Column(db.String(100), nullable=False)
    confidence = db.Column(db.Float, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    def __init__(self, user_id: int, predicted_class: str, confidence: float, **kwargs):
        super().__init__(**kwargs)
        self.user_id = user_id
        self.predicted_class = predicted_class
        self.confidence = confidence

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ─────────────────────────────────────────
# PAGE ROUTES
# ─────────────────────────────────────────
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

@app.route("/detect")
@login_required
def detect_page():
    return render_template("detect.html")

@app.route("/leaderboard")
def leaderboard_page():
    return render_template("leaderboard.html")

# ─────────────────────────────────────────
# AUTH API
# ─────────────────────────────────────────
@app.route("/api/register", methods=["POST"])
def api_register():
    data = request.json
    username = data.get("username", "").strip()
    display_name = data.get("display_name", "").strip() or username
    password = data.get("password", "")
    confirm = data.get("confirm", "")
    if not username or not password:
        return jsonify({"error": "Username dan password wajib diisi"}), 400
    if password != confirm:
        return jsonify({"error": "Password tidak cocok"}), 400
    if User.query.filter_by(username=username).first():
        return jsonify({"error": "Username sudah dipakai"}), 400
    user = User(username=username, display_name=display_name)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    return jsonify({"message": "Berhasil mendaftar!"}), 201

@app.route("/api/login", methods=["POST"])
def api_login():
    data = request.json
    username = data.get("username", "").strip()
    password = data.get("password", "")
    user = User.query.filter_by(username=username).first()
    if not user or not user.check_password(password):
        return jsonify({"error": "Username atau password salah"}), 401
    login_user(user)
    return jsonify({"message": "Berhasil masuk", "display_name": user.display_name})

@app.route("/api/logout", methods=["POST"])
@login_required
def api_logout():
    logout_user()
    return jsonify({"message": "Berhasil keluar"})

@app.route("/api/me")
def api_me():
    if current_user.is_authenticated:
        return jsonify({
            "username": current_user.username,
            "display_name": current_user.display_name,
            "best_score": current_user.best_score or 0
        })
    return jsonify({"authenticated": False}), 200

# ─────────────────────────────────────────
# QUIZ SESSION API (5 soal per percobaan)
# ─────────────────────────────────────────
@app.route("/api/quiz/questions")
@login_required
def api_quiz_questions():
    """Ambil 5 soal acak beserta pilihan (tanpa flag jawaban benar)."""
    all_qs = Question.query.all()
    count = min(5, len(all_qs))
    selected = random.sample(all_qs, count) if len(all_qs) >= count else all_qs
    result = []
    for q in selected:
        choices = [{"id": c.id, "text": c.text} for c in q.choices]
        random.shuffle(choices)
        result.append({
            "id": q.id,
            "text": q.text,
            "category": q.category,
            "choices": choices
        })
    return jsonify({"questions": result})

@app.route("/api/quiz/submit", methods=["POST"])
@login_required
def api_quiz_submit():
    """Submit semua jawaban sekaligus. Hitung skor, simpan percobaan, bandingkan rekor."""
    data = request.json
    answers = data.get("answers", [])   # [{question_id, choice_id}, ...]

    correct_count = 0
    results = []
    for ans in answers:
        qid = ans.get("question_id")
        cid = ans.get("choice_id")
        q = Question.query.get(qid)
        if not q:
            continue
        chosen = Choice.query.filter_by(id=cid, question_id=qid).first()
        correct_choice = Choice.query.filter_by(question_id=qid, is_correct=True).first()
        is_correct = bool(chosen and chosen.is_correct)
        if is_correct:
            correct_count += 1
        results.append({
            "question_id": qid,
            "question_text": q.text,
            "your_answer": chosen.text if chosen else "Tidak dijawab",
            "correct": is_correct,
            "correct_answer": correct_choice.text if correct_choice else "-"
        })

    total = len(answers)
    score_pct = round((correct_count / total * 100) if total > 0 else 0, 1)

    previous_best = current_user.best_score or 0.0
    is_new_best = score_pct > previous_best
    if is_new_best:
        current_user.best_score = score_pct

    attempt = Attempt(
        user_id=current_user.id,
        total_questions=total,
        correct_answers=correct_count,
        score_pct=score_pct
    )
    db.session.add(attempt)
    db.session.commit()

    return jsonify({
        "score_pct": score_pct,
        "correct": correct_count,
        "total": total,
        "previous_best": previous_best,
        "is_new_best": is_new_best,
        "results": results
    })

# ─────────────────────────────────────────
# SKOR WIDGET (pojok kanan atas)
# ─────────────────────────────────────────
@app.route("/api/scores")
def api_scores():
    """Skor tertinggi global dan skor terbaik user aktif."""
    top_user = User.query.order_by(User.best_score.desc()).first()
    global_best = top_user.best_score if top_user else 0
    global_best_name = top_user.display_name if top_user else "-"

    user_best = 0
    if current_user.is_authenticated:
        user_best = current_user.best_score or 0

    return jsonify({
        "global_best": global_best,
        "global_best_name": global_best_name,
        "user_best": user_best
    })

# ─────────────────────────────────────────
# IMAGE DETECTION API
# ─────────────────────────────────────────
@app.route("/api/detect/save", methods=["POST"])
@login_required
def api_detect_save():
    """Simpan hasil deteksi gambar ke database."""
    data = request.json
    predicted_class = data.get("predicted_class", "").strip()
    confidence = float(data.get("confidence", 0))
    if not predicted_class:
        return jsonify({"error": "Data deteksi tidak valid"}), 400
    detection = ImageDetection(
        user_id=current_user.id,
        predicted_class=predicted_class,
        confidence=round(confidence, 4)
    )
    db.session.add(detection)
    db.session.commit()
    return jsonify({"message": "Hasil deteksi disimpan!", "id": detection.id})

@app.route("/api/detect/history")
@login_required
def api_detect_history():
    """Riwayat 10 deteksi terakhir user yang sedang login."""
    detections = (ImageDetection.query
                  .filter_by(user_id=current_user.id)
                  .order_by(ImageDetection.timestamp.desc())
                  .limit(10).all())
    return jsonify([{
        "id": d.id,
        "predicted_class": d.predicted_class,
        "confidence": d.confidence,
        "timestamp": d.timestamp.strftime("%d %b %Y %H:%M")
    } for d in detections])

# ─────────────────────────────────────────
# LEADERBOARD API
# ─────────────────────────────────────────
@app.route("/api/leaderboard")
def api_leaderboard():
    users = User.query.order_by(User.best_score.desc(), User.created_at).limit(50).all()
    return jsonify([{
        "display_name": u.display_name,
        "username": u.username,
        "best_score": u.best_score or 0
    } for u in users])

# ─────────────────────────────────────────
# WEATHER API
# ─────────────────────────────────────────
@app.route("/api/weather")
def api_weather():
    city = request.args.get("city", "").strip()
    api_key = app.config.get("OPENWEATHER_API_KEY") or os.environ.get("OPENWEATHER_API_KEY")
    if not city:
        return jsonify({"error": "Nama kota wajib diisi"}), 400
    if not api_key:
        return jsonify({"error": "API key cuaca belum dikonfigurasi"}), 500
    try:
        geo_url = f"http://api.openweathermap.org/geo/1.0/direct?q={city}&limit=1&appid={api_key}"
        gresp = requests.get(geo_url, timeout=5).json()
        if not gresp:
            return jsonify({"error": "Kota tidak ditemukan"}), 404
        lat = gresp[0]['lat']
        lon = gresp[0]['lon']
        onecall = (
            f"https://api.openweathermap.org/data/2.5/onecall"
            f"?lat={lat}&lon={lon}&exclude=minutely,hourly,alerts"
            f"&units=metric&appid={api_key}"
        )
        j = requests.get(onecall, timeout=5).json()
        daily = j.get("daily", [])[:3]
        result = []
        for d in daily:
            dt = datetime.utcfromtimestamp(d["dt"]) + timedelta(seconds=j.get("timezone_offset", 0))
            result.append({
                "date": dt.strftime("%Y-%m-%d"),
                "day": dt.strftime("%A"),
                "temp_day": d["temp"]["day"],
                "temp_night": d["temp"]["night"],
                "weather": d["weather"][0]["description"]
            })
        return jsonify({"city": city, "forecast": result})
    except Exception as e:
        return jsonify({"error": "Gagal mengambil data cuaca", "detail": str(e)}), 500

# ─────────────────────────────────────────
# CLI & MAIN
# ─────────────────────────────────────────
@app.cli.command("initdb")
def initdb():
    db.create_all()
    print("Database berhasil diinisialisasi.")

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
