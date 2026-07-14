from app import app, db, Question, Choice

def seed():
    with app.app_context():
        db.drop_all()
        db.create_all()

        questions = [
            # ── NLP ──────────────────────────────────────────────────────────
            {
                "text": "Apa kepanjangan dari NLP dalam pemrograman AI?",
                "category": "nlp",
                "choices": [
                    ("Natural Language Processing", True),
                    ("Neural Linear Programming", False),
                    ("Numeric Log Processing", False),
                    ("Network Language Protocol", False),
                ]
            },
            {
                "text": "Model AI mana yang biasa dipakai untuk pemrosesan bahasa alami?",
                "category": "nlp",
                "choices": [
                    ("Transformer (mis. BERT)", True),
                    ("K-means", False),
                    ("DBSCAN", False),
                    ("Linear Regression", False),
                ]
            },
            {
                "text": "Library Python manakah yang paling populer untuk tugas NLP?",
                "category": "nlp",
                "choices": [
                    ("NLTK / spaCy / HuggingFace Transformers", True),
                    ("NumPy", False),
                    ("Matplotlib", False),
                    ("SQLAlchemy", False),
                ]
            },

            # ── Computer Vision ───────────────────────────────────────────────
            {
                "text": "Manakah pustaka Python yang populer untuk Computer Vision?",
                "category": "computer_vision",
                "choices": [
                    ("OpenCV", True),
                    ("Pandas", False),
                    ("Requests", False),
                    ("Flask", False),
                ]
            },
            {
                "text": "Apa fungsi utama algoritma YOLO dalam Computer Vision?",
                "category": "computer_vision",
                "choices": [
                    ("Deteksi objek secara real-time dalam satu kali melewati jaringan", True),
                    ("Mengompresi gambar agar ukurannya lebih kecil", False),
                    ("Menerjemahkan teks dari gambar", False),
                    ("Menggabungkan beberapa gambar menjadi satu", False),
                ]
            },
            {
                "text": "Dalam pengolahan citra, apa yang dimaksud dengan 'bounding box'?",
                "category": "computer_vision",
                "choices": [
                    ("Kotak persegi panjang yang menandai lokasi objek terdeteksi", True),
                    ("Ukuran resolusi gambar dalam piksel", False),
                    ("Filter yang memperhalus tepi gambar", False),
                    ("Nama format file gambar terkompresi", False),
                ]
            },

            # ── Discord.py ────────────────────────────────────────────────────
            {
                "text": "Decorator apa yang digunakan Discord.py untuk mendefinisikan perintah bot?",
                "category": "discord",
                "choices": [
                    ("@bot.command()", True),
                    ("@app.route()", False),
                    ("@bot.event()", False),
                    ("@discord.slash()", False),
                ]
            },
            {
                "text": "Event apa yang dipanggil saat bot Discord berhasil terhubung dan siap menerima pesan?",
                "category": "discord",
                "choices": [
                    ("on_ready", True),
                    ("on_connect", False),
                    ("on_start", False),
                    ("on_login", False),
                ]
            },

            # ── Flask ─────────────────────────────────────────────────────────
            {
                "text": "Decorator apa yang digunakan Flask untuk mendefinisikan sebuah URL route?",
                "category": "flask",
                "choices": [
                    ("@app.route()", True),
                    ("@app.url()", False),
                    ("@flask.path()", False),
                    ("@app.endpoint()", False),
                ]
            },
            {
                "text": "Template engine apa yang digunakan Flask secara default?",
                "category": "flask",
                "choices": [
                    ("Jinja2", True),
                    ("Mako", False),
                    ("Django Templates", False),
                    ("Mustache", False),
                ]
            },
        ]

        for q_data in questions:
            q = Question(text=q_data["text"], category=q_data["category"])
            db.session.add(q)
            db.session.flush()
            for text, is_correct in q_data["choices"]:
                db.session.add(Choice(question_id=q.id, text=text, is_correct=is_correct))

        db.session.commit()
        print(f"Selesai! {len(questions)} soal berhasil ditambahkan.")
        print("Kategori: NLP (3), Computer Vision (3), Discord.py (2), Flask (2)")

if __name__ == "__main__":
    seed()
