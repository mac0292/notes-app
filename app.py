from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash
from database import get_connection, init_db
import os

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY")
init_db()

# ─── Homepage ────────────────────────────────────────────
@app.route("/")
def index():
    if "user_id" not in session:
        return redirect(url_for("login"))
    query = request.args.get("q", "")
    conn = get_connection()
    cur = conn.cursor()
    if query:
        cur.execute(
            """SELECT * FROM notes
               WHERE user_id = %s AND (title ILIKE %s OR content ILIKE %s)
               ORDER BY created DESC""",
            (session["user_id"], f"%{query}%", f"%{query}%")
        )
    else:
        cur.execute(
            "SELECT * FROM notes WHERE user_id = %s ORDER BY created DESC",
            (session["user_id"],)
        )
    notes = cur.fetchall()
    cur.close()
    conn.close()
    return render_template("index.html", notes=notes, query=query)

# ─── Signup ──────────────────────────────────────────────
@app.route("/signup", methods=["GET", "POST"])
def signup():
    error = None
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        hashed   = generate_password_hash(password)
        try:
            conn = get_connection()
            cur  = conn.cursor()
            cur.execute(
                "INSERT INTO users (username, password) VALUES (%s, %s)",
                (username, hashed)
            )
            conn.commit()
            cur.close()
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
        cur  = conn.cursor()
        cur.execute(
            "SELECT * FROM users WHERE username = %s", (username,)
        )
        user = cur.fetchone()
        cur.close()
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
        cur  = conn.cursor()
        cur.execute(
            "INSERT INTO notes (user_id, title, content) VALUES (%s, %s, %s)",
            (session["user_id"], title, content)
        )
        conn.commit()
        cur.close()
        conn.close()
        return redirect(url_for("index"))
    return render_template("note.html", note=None)

# ─── View Note ───────────────────────────────────────────
@app.route("/note/<int:note_id>")
def view_note(note_id):
    if "user_id" not in session:
        return redirect(url_for("login"))
    conn = get_connection()
    cur  = conn.cursor()
    cur.execute(
        "SELECT * FROM notes WHERE id = %s AND user_id = %s",
        (note_id, session["user_id"])
    )
    note = cur.fetchone()
    cur.close()
    conn.close()
    return render_template("view.html", note=note)

# ─── Edit Note ───────────────────────────────────────────
@app.route("/edit/<int:note_id>", methods=["GET", "POST"])
def edit_note(note_id):
    if "user_id" not in session:
        return redirect(url_for("login"))
    conn = get_connection()
    cur  = conn.cursor()
    cur.execute(
        "SELECT * FROM notes WHERE id = %s AND user_id = %s",
        (note_id, session["user_id"])
    )
    note = cur.fetchone()
    if request.method == "POST":
        title   = request.form["title"]
        content = request.form["content"]
        cur.execute(
            "UPDATE notes SET title = %s, content = %s WHERE id = %s AND user_id = %s",
            (title, content, note_id, session["user_id"])
        )
        conn.commit()
        cur.close()
        conn.close()
        return redirect(url_for("index"))
    cur.close()
    conn.close()
    return render_template("note.html", note=note)

# ─── Delete Note ─────────────────────────────────────────
@app.route("/delete/<int:note_id>")
def delete_note(note_id):
    if "user_id" not in session:
        return redirect(url_for("login"))
    conn = get_connection()
    cur  = conn.cursor()
    cur.execute(
        "DELETE FROM notes WHERE id = %s AND user_id = %s",
        (note_id, session["user_id"])
    )
    conn.commit()
    cur.close()
    conn.close()
    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(debug=True)