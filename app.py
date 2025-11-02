from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime
import os
import cloudinary
import cloudinary.uploader
import cloudinary.api

# ---------- SETUP ----------
app = Flask(__name__)
app.config['SECRET_KEY'] = 'dev-secret'
db_url = os.getenv("DATABASE_URL", "sqlite:///diary.db")
app.config["SQLALCHEMY_DATABASE_URI"] = db_url

# Cloudinary Konfiguration
cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
    secure=True
)

# absoluter Pfad für lokale Uploads (Backup-Funktion)
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

db = SQLAlchemy(app)

# ---------- DATABASE ----------
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(300), unique=True, nullable=False)
    password = db.Column(db.String(300), nullable=False)
    entries = db.relationship('Entry', backref='user', lazy=True)

class Entry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    image_filename = db.Column(db.String(300))
    date = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

# ---------- ROUTES ----------
@app.route('/')
def home():
    user_email = session.get('user')
    if not user_email:
        return render_template('index.html', user=None)
    user = User.query.filter_by(email=user_email).first()
    entries = Entry.query.filter_by(user_id=user.id).order_by(Entry.date.desc()).all()
    return render_template('index.html', user=user.email, entries=entries)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        if User.query.filter_by(email=email).first():
            flash('Email already exists!')
            return redirect(url_for('register'))
        hashed = generate_password_hash(password)
        new_user = User(email=email, password=hashed)
        db.session.add(new_user)
        db.session.commit()
        flash('Registration successful! Please login.')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            session['user'] = email
            flash('Login successful!')
            return redirect(url_for('home'))
        else:
            flash('Wrong email or password.')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user', None)
    flash('Logged out successfully.')
    return redirect(url_for('home'))

@app.route('/add', methods=['GET', 'POST'])
def add_entry():
    if 'user' not in session:
        flash('Please log in first.')
        return redirect(url_for('login'))

    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        file = request.files.get('image')

        image_url = None
        if file and file.filename != '':
            # Hochladen zu Cloudinary
            upload_result = cloudinary.uploader.upload(file, folder="online_diary")
            image_url = upload_result.get("secure_url")
            print("✅ Uploaded to Cloudinary:", image_url)

        user = User.query.filter_by(email=session['user']).first()
        new_entry = Entry(title=title, content=content, image_filename=image_url, user_id=user.id)
        db.session.add(new_entry)
        db.session.commit()
        flash('New entry added!')
        return redirect(url_for('home'))

    return render_template('add.html')

@app.route('/delete/<int:id>')
def delete_entry(id):
    if 'user' not in session:
        return redirect(url_for('login'))
    entry = Entry.query.get_or_404(id)
    user = User.query.filter_by(email=session['user']).first()
    if entry.user_id != user.id:
        flash('Not allowed.')
        return redirect(url_for('home'))
    db.session.delete(entry)
    db.session.commit()
    flash('Entry deleted.')
    return redirect(url_for('home'))

# ---------- DB SETUP ----------
if not os.path.exists('instance'):
    os.mkdir('instance')
with app.app_context():
    os.makedirs(os.path.join("static", "uploads"), exist_ok=True)
    db.create_all()

if __name__ == '__main__':
    print(f"📁 Upload folder: {UPLOAD_FOLDER}")
    app.run(debug=True)
