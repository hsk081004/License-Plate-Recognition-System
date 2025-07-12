from flask import Flask, render_template, request, redirect, session, url_for
import os
import sqlite3
from werkzeug.utils import secure_filename
from lpr_engine import process_license_plate

# --- Path Configuration ---
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
STATIC_FOLDER = os.path.join(BASE_DIR, 'static')
TEMPLATES_FOLDER = os.path.join(BASE_DIR, 'templates')
UPLOAD_FOLDER = os.path.join(STATIC_FOLDER, 'uploads')
DATABASE_PATH = os.path.join(BASE_DIR, 'database.db')

app = Flask(__name__, static_folder=STATIC_FOLDER,
            template_folder=TEMPLATES_FOLDER)
app.secret_key = 'your_secret_key'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# ------------------ DATABASE CONNECTION ------------------


def get_db_connection():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# ------------------ HOME PAGE ------------------


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        if 'username' not in session:
            return redirect(url_for('auth_required'))
        return redirect(url_for('dashboard'))
    return render_template('index.html')

# ------------------ AUTH REQUIRED ------------------


@app.route('/auth-required')
def auth_required():
    return render_template('auth_required.html')

# ------------------ LOGIN ------------------


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = get_db_connection()
        user = conn.execute(
            "SELECT * FROM users WHERE username=? AND password=?", (
                username, password)
        ).fetchone()
        conn.close()
        if user:
            session['username'] = username
            if username == 'admin':
                return redirect(url_for('user_stats'))
            return redirect(url_for('dashboard'))
        else:
            return render_template('login.html', error="Invalid credentials.")
    return render_template('login.html')

# ------------------ SIGNUP ------------------


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = get_db_connection()
        try:
            conn.execute(
                "INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
            conn.commit()
            conn.close()
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            conn.close()
            return render_template('signup.html', error="Username already taken.")
    return render_template('signup.html')

# ------------------ LOGOUT ------------------


@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

# ------------------ DASHBOARD / OCR ------------------


@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if 'username' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        if 'file' not in request.files:
            return "No file part", 400
        file = request.files['file']
        if file.filename == '':
            return "No selected file", 400

        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        # Run the license plate recognition pipeline
        plate_texts, cropped_paths = process_license_plate(filepath)

        # Convert to list if necessary
        if isinstance(plate_texts, str):
            plate_texts = [plate_texts]
        if isinstance(cropped_paths, str):
            cropped_paths = [cropped_paths]

        # Save to database
        conn = get_db_connection()
        for text in plate_texts:
            conn.execute(
                "INSERT INTO history (username, image_path, plate_text) VALUES (?, ?, ?)",
                (session['username'], filename, text)
            )
        conn.commit()
        conn.close()

        original_rel_path = os.path.relpath(
            filepath, STATIC_FOLDER).replace('\\', '/')
        cropped_rel_paths = [os.path.relpath(p, STATIC_FOLDER).replace(
            '\\', '/') for p in cropped_paths]

        return render_template('result.html',
                               plate=' | '.join(plate_texts),
                               original_image=original_rel_path,
                               cropped_image=cropped_rel_paths)

    return render_template('dashboard.html')

# ------------------ HISTORY ------------------


@app.route('/history')
def history():
    if 'username' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    rows = conn.execute(
        'SELECT * FROM history WHERE username = ? ORDER BY timestamp DESC',
        (session['username'],)
    ).fetchall()
    conn.close()
    return render_template('history.html', records=rows)

# ------------------ ADMIN STATS ------------------


@app.route('/admin/users')
def user_stats():
    if 'username' not in session or session['username'] != 'admin':
        return redirect(url_for('dashboard'))

    conn = get_db_connection()
    users = conn.execute('''
        SELECT username, COUNT(*) AS total_uploads
        FROM history
        GROUP BY username
    ''').fetchall()
    conn.close()
    return render_template('user_stats.html', users=users)


# ------------------ RUN ------------------
if __name__ == '__main__':
    app.run(debug=True)
