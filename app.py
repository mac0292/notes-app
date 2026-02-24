from flask import Flask, render_template, request, redirect, url_for
from database import get_connection, init_db

app = Flask(__name__)

# ─── Homepage: show all notes ───────────────────────────
@app.route("/")
def index():
    conn = get_connection()
    notes = conn.execute(
        "SELECT * FROM notes ORDER BY created DESC"
    ).fetchall()
    conn.close()
    return render_template("index.html", notes=notes)

# ─── New Note ───────────────────────────────────────────
@app.route("/new", methods=["GET", "POST"])
def new_note():
    if request.method == "POST":
        title   = request.form["title"]
        content = request.form["content"]
        conn = get_connection()
        conn.execute(
            "INSERT INTO notes (title, content) VALUES (?, ?)",
            (title, content)
        )
        conn.commit()
        conn.close()
        return redirect(url_for("index"))
    return render_template("note.html", note=None)

# ─── View Single Note ────────────────────────────────────
@app.route("/note/<int:note_id>")
def view_note(note_id):
    conn = get_connection()
    note = conn.execute(
        "SELECT * FROM notes WHERE id = ?", (note_id,)
    ).fetchone()
    conn.close()
    return render_template("view.html", note=note)

# ─── Edit Note ───────────────────────────────────────────
@app.route("/edit/<int:note_id>", methods=["GET", "POST"])
def edit_note(note_id):
    conn = get_connection()
    note = conn.execute(
        "SELECT * FROM notes WHERE id = ?", (note_id,)
    ).fetchone()
    if request.method == "POST":
        title   = request.form["title"]
        content = request.form["content"]
        conn.execute(
            "UPDATE notes SET title = ?, content = ? WHERE id = ?",
            (title, content, note_id)
        )
        conn.commit()
        conn.close()
        return redirect(url_for("index"))
    conn.close()
    return render_template("note.html", note=note)

# ─── Delete Note ─────────────────────────────────────────
@app.route("/delete/<int:note_id>")
def delete_note(note_id):
    conn = get_connection()
    conn.execute("DELETE FROM notes WHERE id = ?", (note_id,))
    conn.commit()
    conn.close()
    return redirect(url_for("index"))

# ─── Start the app ───────────────────────────────────────
if __name__ == "__main__":
    init_db()
    app.run(debug=True)