from app import app, db, Question, Choice
def seed():
    with app.app_context():
        # hapus dulu
        db.drop_all()
        db.create_all()
        # contoh pertanyaan
        q1 = Question(text="Apa kepanjangan dari NLP dalam pemrograman?", category="nlp")
        db.session.add(q1); db.session.flush()
        db.session.add_all([
            Choice(question_id=q1.id, text="Natural Language Processing", is_correct=True),
            Choice(question_id=q1.id, text="Neural Linear Programming", is_correct=False),
            Choice(question_id=q1.id, text="Numeric Log Processing", is_correct=False),
            Choice(question_id=q1.id, text="Network Language Protocol", is_correct=False)
        ])
        q2 = Question(text="Manakah pustaka Python yang populer untuk visi komputer?", category="vision")
        db.session.add(q2); db.session.flush()
        db.session.add_all([
            Choice(question_id=q2.id, text="OpenCV", is_correct=True),
            Choice(question_id=q2.id, text="Pandas", is_correct=False),
            Choice(question_id=q2.id, text="Requests", is_correct=False),
            Choice(question_id=q2.id, text="Flask", is_correct=False)
        ])
        q3 = Question(text="Model AI mana yang biasa dipakai untuk pemrosesan bahasa alami?", category="nlp")
        db.session.add(q3); db.session.flush()
        db.session.add_all([
            Choice(question_id=q3.id, text="Transformer (mis. BERT)", is_correct=True),
            Choice(question_id=q3.id, text="K-means", is_correct=False),
            Choice(question_id=q3.id, text="DBSCAN", is_correct=False),
            Choice(question_id=q3.id, text="Linear Regression", is_correct=False)
        ])
        db.session.commit()
        print("seeded db")

if __name__ == "__main__":
    seed()
