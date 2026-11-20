
import os
import sqlite3
from functools import wraps
from datetime import datetime
from flask import (
    Flask, request, redirect, url_for,
    session, flash, send_from_directory,
    render_template_string
)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "TML_CHANGE_THIS_SECRET_KEY_2026"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "tml_videos")
DB_PATH = os.path.join(BASE_DIR, "tml.db")

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

ALLOWED_EXTENSIONS = {"mp4", "webm", "mov", "m4v"}
app.config["MAX_CONTENT_LENGTH"] = 2 * 1024 * 1024 * 1024

def db():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con

def setup():
    con = db()
    con.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT DEFAULT 'creator',
            premium INTEGER DEFAULT 0
        )
    """)
    con.execute("""
        CREATE TABLE IF NOT EXISTS videos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            category TEXT,
            kind TEXT DEFAULT 'Movie',
            filename TEXT NOT NULL,
            creator TEXT,
            access TEXT DEFAULT 'Free',
            approved INTEGER DEFAULT 0,
            created_at TEXT
        )
    """)

    admin = con.execute(
        "SELECT id FROM users WHERE username=?",
        ("admin",)
    ).fetchone()

    if not admin:
        con.execute(
            "INSERT INTO users (username,password,role,premium) VALUES (?,?,?,?)",
            ("admin", generate_password_hash("TMLadmin2026!"), "admin", 1)
        )

    con.commit()
    con.close()

setup()

STYLE = """
<style>
*{box-sizing:border-box}
body{margin:0;background:#0b1020;color:white;font-family:Arial,sans-serif}
header{background:#111a30;padding:18px;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap}
.logo{font-size:21px;font-weight:bold;color:#f5bd24}
nav a{color:white;text-decoration:none;margin:7px;font-size:14px}
main{padding:20px;max-width:1100px;margin:auto}
.hero{background:linear-gradient(120deg,#182b52,#51320c);padding:35px 22px;border-radius:16px;margin-bottom:25px}
h1,h2{color:#f5bd24}
input,textarea,select{width:100%;padding:13px;margin:8px 0;border:1px solid #34415d;border-radius:8px;background:#172238;color:white}
button,.btn{background:#f5bd24;color:#111;padding:12px 17px;border:0;border-radius:8px;font-weight:bold;text-decoration:none;display:inline-block;cursor:pointer}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:16px}
.card{background:#172238;border-radius:12px;padding:15px;overflow:hidden}
.card video{width:100%;border-radius:8px;background:black}
.small{color:#aebbd0;font-size:13px}
.tag{color:#f5bd24;font-size:12px}
form{max-width:600px}
a{color:#f5bd24}
footer{text-align:center;padding:30px;color:#8896aa}
.alert{background:#283b28;padding:12px;border-radius:8px;margin:10px 0}
</style>
"""

HEADER = """
<header>
 <div class="logo">🎬 TANZANIA MOVIE LIBRARY</div>
 <nav>
  <a href="/">Home</a>
  <a href="/?kind=Movie">Movies</a>
  <a href="/?kind=Series">Series</a>
  <a href="/upload">Upload</a>
  {% if session.get('username') %}
   <a href="/logout">Logout</a>
  {% else %}
   <a href="/login">Login</a>
   <a href="/register">Register</a>
  {% endif %}
  {% if session.get('role') == 'admin' %}
   <a href="/admin">Admin</a>
  {% endif %}
 </nav>
</header>
"""

def page(content, **kwargs):
    return render_template_string(
        STYLE + HEADER + "<main>" + content + "</main><footer>TML © 2026 | Your World of Movies</footer>",
        **kwargs
    )

def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get("user_id"):
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return wrapper

def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if session.get("role") != "admin":
            return "Access denied", 403
        return f(*args, **kwargs)
    return wrapper

def allowed_file(filename):
    return (
        "." in filename and
        filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
    )

@app.route("/")
def home():
    search = request.args.get("q", "").strip()
    kind = request.args.get("kind", "").strip()

    con = db()
    sql = "SELECT * FROM videos WHERE approved=1"
    params = []

    if search:
        sql += " AND (title LIKE ? OR description LIKE ? OR category LIKE ?)"
        params += [f"%{search}%"] * 3

    if kind in ("Movie", "Series"):
        sql += " AND kind=?"
        params.append(kind)

    sql += " ORDER BY id DESC"
    videos = con.execute(sql, params).fetchall()
    con.close()

    content = """
    <section class="hero">
      <h1>WELCOME TO TML</h1>
      <h3>Your World of Movies</h3>
      <p>Movies • Series • Tanzania • Africa • International</p>
      <p>Watch online and enjoy entertainment.</p>
    </section>

    <form method="get">
      <input name="q" placeholder="Search movies and series..."
       value="{{ request.args.get('q','') }}">
      <button>SEARCH</button>
    </form>

    <h2>Explore Categories</h2>
    <p>
      <a class="btn" href="/?kind=Movie">Movies</a>
      <a class="btn" href="/?kind=Series">Series</a>
      <a class="btn" href="/">All Videos</a>
    </p>

    <h2>Latest Videos</h2>
    <div class="grid">
    {% for v in videos %}
      <div class="card">
        <video controls preload="metadata">
          <source src="{{ url_for('video_file', filename=v['filename']) }}">
        </video>
        <h3>{{ v['title'] }}</h3>
        <p class="small">{{ v['category'] }} | {{ v['kind'] }}</p>
        <p>{{ v['description'] }}</p>
        <p class="tag">{{ v['access'] }}</p>
        <a class="btn" href="{{ url_for('watch', video_id=v['id']) }}">WATCH</a>
      </div>
    {% else %}
      <p>No approved videos yet. Creators can upload videos.</p>
    {% endfor %}
    </div>
    """
    return page(content, videos=videos)

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if len(username) < 3 or len(password) < 6:
            return page("<h2>Registration</h2><p>Username iwe na herufi 3 na password angalau 6.</p><a href='/register'>Try again</a>")

        con = db()
        try:
            con.execute(
                "INSERT INTO users(username,password) VALUES (?,?)",
                (username, generate_password_hash(password))
            )
            con.commit()
            con.close()
            return redirect("/login")
        except sqlite3.IntegrityError:
            con.close()
            return page("<h2>Username tayari inatumika.</h2><a href='/register'>Rudi</a>")

    return page("""
    <h2>Create TML Account</h2>
    <form method="post">
      <input name="username" placeholder="Username" required>
      <input name="password" type="password" placeholder="Password (minimum 6)" required>
      <button>REGISTER</button>
    </form>
    """)

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        con = db()
        user = con.execute(
            "SELECT * FROM users WHERE username=?", (username,)
        ).fetchone()
        con.close()

        if user and check_password_hash(user["password"], password):
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            session["role"] = user["role"]
            session["premium"] = user["premium"]
            return redirect("/")

        return page("<h2>Login failed</h2><p>Username au password si sahihi.</p><a href='/login'>Try again</a>")

    return page("""
    <h2>Login to TML</h2>
    <form method="post">
      <input name="username" placeholder="Username" required>
      <input name="password" type="password" placeholder="Password" required>
      <button>LOGIN</button>
    </form>
    """)

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

@app.route("/upload", methods=["GET", "POST"])
@login_required
def upload():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        category = request.form.get("category", "Other")
        kind = request.form.get("kind", "Movie")
        access = request.form.get("access", "Free")
        file = request.files.get("video")

        if not title or not file or not file.filename:
            return page("<h2>Jaza jina la video na chagua video.</h2><a href='/upload'>Rudi</a>")

        if not allowed_file(file.filename):
            return page("<h2>Video format haikubaliki. Tumia MP4, WEBM, MOV au M4V.</h2><a href='/upload'>Rudi</a>")

        filename = secure_filename(file.filename)
        filename = datetime.now().strftime("%Y%m%d%H%M%S%f") + "_" + filename
        file.save(os.path.join(UPLOAD_FOLDER, filename))

        con = db()
        approved = 1 if session.get("role") == "admin" else 0
        con.execute("""
            INSERT INTO videos
            (title,description,category,kind,filename,creator,access,approved,created_at)
            VALUES (?,?,?,?,?,?,?,?,?)
        """, (
            title, description, category, kind, filename,
            session["username"], access, approved,
            datetime.now().isoformat()
        ))
        con.commit()
        con.close()

        return page("<h2>Video imepokelewa!</h2><p>Video ya Creator itasubiri idhini ya Admin kabla ya kuonekana kwa watazamaji.</p><a class='btn' href='/'>HOME</a>")

    return page("""
    <h2>Upload Video</h2>
    <form method="post" enctype="multipart/form-data">
      <input name="title" placeholder="Video title" required>
      <textarea name="description" placeholder="Description"></textarea>

      <label>Category</label>
      <select name="category">
        <option>Action</option>
        <option>Comedy</option>
        <option>Drama</option>
        <option>Documentary</option>
        <option>Education</option>
        <option>Sports</option>
        <option>Music</option>
        <option>Other</option>
      </select>

      <label>Type</label>
      <select name="kind">
        <option>Movie</option>
        <option>Series</option>
      </select>

      <label>Access</label>
      <select name="access">
        <option>Free</option>
        <option>Premium</option>
      </select>

      <label>Select video</label>
      <input type="file" name="video" accept="video/*" required>
      <button>UPLOAD VIDEO</button>
    </form>
    """)

@app.route("/watch/<int:video_id>")
def watch(video_id):
    con = db()
    v = con.execute(
        "SELECT * FROM videos WHERE id=? AND approved=1",
        (video_id,)
    ).fetchone()
    con.close()

    if not v:
        return "Video haipo", 404

    if v["access"] == "Premium" and not session.get("premium"):
        return page("<h2>Premium Video</h2><p>Video hii inahitaji akaunti ya Premium.</p><p>Malipo ya Premium bado hayajaunganishwa.</p><a href='/'>Back home</a>")

    content = """
    <h2>{{ v['title'] }}</h2>
    <video controls autoplay style="width:100%;max-height:65vh;background:black">
      <source src="{{ url_for('video_file', filename=v['filename']) }}">
    </video>
    <p>{{ v['description'] }}</p>
    <p class="small">{{ v['category'] }} | {{ v['kind'] }} | {{ v['access'] }}</p>
    <a class="btn" href="{{ url_for('download_video', filename=v['filename']) }}">DOWNLOAD</a>
    <p><a href="/">Back to Home</a></p>
    """
    return page(content, v=v)

@app.route("/video/<path:filename>")
def video_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

@app.route("/download/<path:filename>")
@login_required
def download_video(filename):
    con = db()
    v = con.execute(
        "SELECT * FROM videos WHERE filename=? AND approved=1",
        (filename,)
    ).fetchone()
    con.close()

    if not v:
        return "Video haipo", 404

    if v["access"] == "Premium" and not session.get("premium"):
        return "Premium account required", 403

    return send_from_directory(
        UPLOAD_FOLDER, filename, as_attachment=True
    )

@app.route("/admin")
@login_required
@admin_required
def admin():
    con = db()
    pending = con.execute(
        "SELECT * FROM videos WHERE approved=0 ORDER BY id DESC"
    ).fetchall()
    approved = con.execute(
        "SELECT * FROM videos WHERE approved=1 ORDER BY id DESC"
    ).fetchall()
    users = con.execute(
        "SELECT id,username,role,premium FROM users"
    ).fetchall()
    con.close()

    content = """
    <h1>TML ADMIN DASHBOARD</h1>
    <h2>Pending Videos</h2>
    {% for v in pending %}
      <div class="card">
        <h3>{{ v['title'] }}</h3>
        <p>{{ v['creator'] }} | {{ v['category'] }}</p>
        <a class="btn" href="{{ url_for('approve', video_id=v['id']) }}">APPROVE</a>
        <a href="{{ url_for('delete_video', video_id=v['id']) }}">DELETE</a>
      </div>
    {% else %}
      <p>No pending videos.</p>
    {% endfor %}

    <h2>Approved Videos: {{ approved|length }}</h2>
    <h2>Registered Users: {{ users|length }}</h2>
    <div class="grid">
    {% for u in users %}
      <div class="card">
        <b>{{ u['username'] }}</b>
        <p>{{ u['role'] }} | Premium: {{ u['premium'] }}</p>
        {% if u['role'] != 'admin' %}
        <a href="{{ url_for('make_premium', user_id=u['id']) }}">Give Premium</a>
        {% endif %}
      </div>
    {% endfor %}
    </div>
    """
    return page(content, pending=pending, approved=approved, users=users)

@app.route("/admin/approve/<int:video_id>")
@login_required
@admin_required
def approve(video_id):
    con = db()
    con.execute(
        "UPDATE videos SET approved=1 WHERE id=?", (video_id,)
    )
    con.commit()
    con.close()
    return redirect("/admin")

@app.route("/admin/delete/<int:video_id>")
@login_required
@admin_required
def delete_video(video_id):
    con = db()
    v = con.execute(
        "SELECT filename FROM videos WHERE id=?", (video_id,)
    ).fetchone()

    if v:
        path = os.path.join(UPLOAD_FOLDER, v["filename"])
        if os.path.exists(path):
            os.remove(path)
        con.execute("DELETE FROM videos WHERE id=?", (video_id,))
        con.commit()

    con.close()
    return redirect("/admin")

@app.route("/admin/premium/<int:user_id>")
@login_required
@admin_required
def make_premium(user_id):
    con = db()
    con.execute(
        "UPDATE users SET premium=1 WHERE id=?", (user_id,)
    )
    con.commit()
    con.close()
    return redirect("/admin")

@app.errorhandler(413)
def too_large(error):
    return "Video ni kubwa kuliko kiwango kinachoruhusiwa na mfumo.", 413

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
