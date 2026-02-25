from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash
from database import get_connection, init_db

app = Flask(__name__)
app.secret_key = "your-secret-key-change-this"  # needed for sessions
init_db()

# ─── Homepage ────────────────────────────────────────────
@app.route("/")
def index():
    if "user_id" not in session:        # not logged in?
        return redirect(url_for("login"))  # send to login page
    query = request.args.get("q", "")
    conn = get_connection()
    if query:
        notes = conn.execute(
            """SELECT * FROM notes 
               WHERE user_id = ? AND (title LIKE ? OR content LIKE ?)
               ORDER BY created DESC""",
            (session["user_id"], f"%{query}%", f"%{query}%")
        ).fetchall()
    else:
        notes = conn.execute(
            "SELECT * FROM notes WHERE user_id = ? ORDER BY created DESC",
            (session["user_id"],)         # only this user's notes!
        ).fetchall()
    conn.close()
    return render_template("index.html", notes=notes, query=query)

# ─── Signup ──────────────────────────────────────────────
@app.route("/signup", methods=["GET", "POST"])
def signup():
    error = None
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        hashed   = generate_password_hash(password)  # never store plain password!
        try:
            conn = get_connection()
            conn.execute(
                "INSERT INTO users (username, password) VALUES (?, ?)",
                (username, hashed)
            )
            conn.commit()
            conn.close()
            return redirect(url_for("login"))
        except:
            error = "Username already exists. Try another."
    return render_template("signup.html", error=error)

# ─── Login ───────────────────────────────────────────────
@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        conn = get_connection()
        user = conn.execute(
            "SELECT * FROM users WHERE username = ?", (username,)
        ).fetchone()
        conn.close()
        if user and check_password_hash(user["password"], password):
            session["user_id"]  = user["id"]
            session["username"] = user["username"]
            return redirect(url_for("index"))
        else:
            error = "Wrong username or password."
    return render_template("login.html", error=error)

# ─── Logout ──────────────────────────────────────────────
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

# ─── New Note ────────────────────────────────────────────
@app.route("/new", methods=["GET", "POST"])
def new_note():
    if "user_id" not in session:
        return redirect(url_for("login"))
    if request.method == "POST":
        title   = request.form["title"]
        content = request.form["content"]
        conn = get_connection()
        conn.execute(
            "INSERT INTO notes (user_id, title, content) VALUES (?, ?, ?)",
            (session["user_id"], title, content)
        )
        conn.commit()
        conn.close()
        return redirect(url_for("index"))
    return render_template("note.html", note=None)

# ─── View Note ───────────────────────────────────────────
@app.route("/note/<int:note_id>")
def view_note(note_id):
    if "user_id" not in session:
        return redirect(url_for("login"))
    conn = get_connection()
    note = conn.execute(
        "SELECT * FROM notes WHERE id = ? AND user_id = ?",
        (note_id, session["user_id"])
    ).fetchone()
    conn.close()
    return render_template("view.html", note=note)

# ─── Edit Note ───────────────────────────────────────────
@app.route("/edit/<int:note_id>", methods=["GET", "POST"])
def edit_note(note_id):
    if "user_id" not in session:
        return redirect(url_for("login"))
    conn = get_connection()
    note = conn.execute(
        "SELECT * FROM notes WHERE id = ? AND user_id = ?",
        (note_id, session["user_id"])
    ).fetchone()
    if request.method == "POST":
        title   = request.form["title"]
        content = request.form["content"]
        conn.execute(
            "UPDATE notes SET title = ?, content = ? WHERE id = ? AND user_id = ?",
            (title, content, note_id, session["user_id"])
        )
        conn.commit()
        conn.close()
        return redirect(url_for("index"))
    conn.close()
    return render_template("note.html", note=note)

# ─── Delete Note ─────────────────────────────────────────
@app.route("/delete/<int:note_id>")
def delete_note(note_id):
    if "user_id" not in session:
        return redirect(url_for("login"))
    conn = get_connection()
    conn.execute(
        "DELETE FROM notes WHERE id = ? AND user_id = ?",
        (note_id, session["user_id"])
    )
    conn.commit()
    conn.close()
    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(debug=True)
