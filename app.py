from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash
from database import get_connection, init_db
from dotenv import load_dotenv
load_dotenv()
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
# ─── Chat Page ────────────────────────────────────────@app.route("/chat", methods=["GET"])
# ─── Chat Page ───────────────────────────────────────────
@app.route("/chat", methods=["GET"])
def chat():
    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_connection()
    cur  = conn.cursor()

    # Create persona if first time
    cur.execute(
        "SELECT * FROM personas WHERE user_id = %s",
        (session["user_id"],)
    )
    persona = cur.fetchone()
    if not persona:
        cur.execute(
            "INSERT INTO personas (user_id) VALUES (%s)",
            (session["user_id"],)
        )
        conn.commit()
        persona = {"onboarded": False, "goals": "", "habits": "", "summary": ""}

    # Load today's chat history
    cur.execute(
        """SELECT role, content FROM chats
           WHERE user_id = %s
           AND created::date = CURRENT_DATE
           ORDER BY created ASC""",
        (session["user_id"],)
    )
    history = [dict(row) for row in cur.fetchall()]

    # If no history today → generate opening message from AI
    if not history:
        from ai import get_ai_response
        opening = get_ai_response([], persona, has_history=False)
        cur.execute(
            "INSERT INTO chats (user_id, role, content) VALUES (%s, %s, %s)",
            (session["user_id"], "assistant", opening)
        )
        conn.commit()
        history = [{"role": "assistant", "content": opening}]

    cur.close()
    conn.close()

    return render_template("chat.html", history=history)


# ─── Chat Message ─────────────────────────────────────────
@app.route("/chat/message", methods=["POST"])
def chat_message():
    if "user_id" not in session:
        return redirect(url_for("login"))

    user_message = request.form["message"]
    user_id      = session["user_id"]

    conn = get_connection()
    cur  = conn.cursor()

    # Load persona
    cur.execute(
        "SELECT * FROM personas WHERE user_id = %s",
        (user_id,)
    )
    persona = cur.fetchone()

    # Load today's chat history
    cur.execute(
        """SELECT role, content FROM chats
           WHERE user_id = %s
           AND created::date = CURRENT_DATE
           ORDER BY created ASC""",
        (user_id,)
    )
    history = [dict(row) for row in cur.fetchall()]

    # Save user message
    cur.execute(
        "INSERT INTO chats (user_id, role, content) VALUES (%s, %s, %s)",
        (user_id, "user", user_message)
    )
    conn.commit()

    history.append({"role": "user", "content": user_message})

    # Get AI response
    from ai import get_ai_response, extract_persona, create_or_update_journal
    has_history = len(history) > 1   # more than just the user's first message
    ai_reply = get_ai_response(history, persona, has_history)

    # Save AI response
    cur.execute(
        "INSERT INTO chats (user_id, role, content) VALUES (%s, %s, %s)",
        (user_id, "assistant", ai_reply)
    )
    conn.commit()

    history.append({"role": "assistant", "content": ai_reply})

    # ── Handle onboarding complete ────────────────────────
    if "[ONBOARDING_COMPLETE]" in ai_reply:
        persona_data = extract_persona(history)
        cur.execute(
            """UPDATE personas
               SET goals = %s, habits = %s, summary = %s, onboarded = TRUE
               WHERE user_id = %s""",
            (persona_data["goals"], persona_data["habits"],
             persona_data["summary"], user_id)
        )
        conn.commit()
        ai_reply = ai_reply.replace("[ONBOARDING_COMPLETE]", "").strip()

    # ── Save/update journal after every user message ──────
    if persona and persona["onboarded"]:
        # Check if today's journal entry exists
        cur.execute(
            """SELECT dj.note_id, n.content FROM daily_journals dj
               JOIN notes n ON n.id = dj.note_id
               WHERE dj.user_id = %s AND dj.date = CURRENT_DATE""",
            (user_id,)
        )
        existing = cur.fetchone()

        # Create or update journal entry
        existing_content = existing["content"] if existing else None
        title, content   = create_or_update_journal(
            history, persona, existing_content
        )

        if existing:
            # Update existing note
            cur.execute(
                "UPDATE notes SET title = %s, content = %s WHERE id = %s",
                (title, content, existing["note_id"])
            )
        else:
            # Create new note
            cur.execute(
                """INSERT INTO notes (user_id, title, content)
                   VALUES (%s, %s, %s) RETURNING id""",
                (user_id, title, content)
            )
            note_id = cur.fetchone()["id"]
            cur.execute(
                """INSERT INTO daily_journals (user_id, note_id)
                   VALUES (%s, %s)""",
                (user_id, note_id)
            )

        # Update persona
        persona_data = extract_persona(history)
        cur.execute(
            """UPDATE personas
               SET goals = %s, habits = %s, summary = %s, updated_at = NOW()
               WHERE user_id = %s""",
            (persona_data["goals"], persona_data["habits"],
             persona_data["summary"], user_id)
        )
        conn.commit()

    # ── Handle journal ready signal ───────────────────────
    if "[JOURNAL_READY]" in ai_reply:
        ai_reply = ai_reply.replace("[JOURNAL_READY]", "").strip()
        ai_reply += "\n\n✅ Today's journal entry saved to your notes!"

    cur.close()
    conn.close()

    return redirect(url_for("chat"))

# ─── Chat API (AJAX) ─────────────────────────────────────
@app.route("/chat/send", methods=["POST"])
def chat_send():
    if "user_id" not in session:
        return {"error": "Not logged in"}, 401

    user_message = request.json.get("message")
    user_id      = session["user_id"]

    conn = get_connection()
    cur  = conn.cursor()

    # Load persona
    cur.execute(
        "SELECT * FROM personas WHERE user_id = %s",
        (user_id,)
    )
    persona = cur.fetchone()

    # Load today's history
    cur.execute(
        """SELECT role, content FROM chats
           WHERE user_id = %s
           AND created::date = CURRENT_DATE
           ORDER BY created ASC""",
        (user_id,)
    )
    history = [dict(row) for row in cur.fetchall()]

    # Save user message
    cur.execute(
        "INSERT INTO chats (user_id, role, content) VALUES (%s, %s, %s)",
        (user_id, "user", user_message)
    )
    conn.commit()

    history.append({"role": "user", "content": user_message})

    # Get AI response
    from ai import get_ai_response, extract_persona, create_or_update_journal
    has_history = len(history) > 1
    ai_reply    = get_ai_response(history, persona, has_history)

    # Save AI response
    cur.execute(
        "INSERT INTO chats (user_id, role, content) VALUES (%s, %s, %s)",
        (user_id, "assistant", ai_reply)
    )
    conn.commit()

    history.append({"role": "assistant", "content": ai_reply})

    # Handle onboarding
    if "[ONBOARDING_COMPLETE]" in ai_reply:
        persona_data = extract_persona(history)
        cur.execute(
            """UPDATE personas
               SET goals = %s, habits = %s, summary = %s, onboarded = TRUE
               WHERE user_id = %s""",
            (persona_data["goals"], persona_data["habits"],
             persona_data["summary"], user_id)
        )
        conn.commit()
        ai_reply = ai_reply.replace("[ONBOARDING_COMPLETE]", "").strip()

    # Save/update journal
    if persona and persona["onboarded"]:
        cur.execute(
            """SELECT dj.note_id, n.content FROM daily_journals dj
               JOIN notes n ON n.id = dj.note_id
               WHERE dj.user_id = %s AND dj.date = CURRENT_DATE""",
            (user_id,)
        )
        existing        = cur.fetchone()
        existing_content = existing["content"] if existing else None
        title, content  = create_or_update_journal(
            history, persona, existing_content
        )
        if existing:
            cur.execute(
                "UPDATE notes SET title = %s, content = %s WHERE id = %s",
                (title, content, existing["note_id"])
            )
        else:
            cur.execute(
                """INSERT INTO notes (user_id, title, content)
                   VALUES (%s, %s, %s) RETURNING id""",
                (user_id, title, content)
            )
            note_id = cur.fetchone()["id"]
            cur.execute(
                "INSERT INTO daily_journals (user_id, note_id) VALUES (%s, %s)",
                (user_id, note_id)
            )
        persona_data = extract_persona(history)
        cur.execute(
            """UPDATE personas
               SET goals = %s, habits = %s, summary = %s, updated_at = NOW()
               WHERE user_id = %s""",
            (persona_data["goals"], persona_data["habits"],
             persona_data["summary"], user_id)
        )
        conn.commit()

    # Handle journal ready
    journal_saved = False
    if "[JOURNAL_READY]" in ai_reply:
        ai_reply     = ai_reply.replace("[JOURNAL_READY]", "").strip()
        journal_saved = True

    cur.close()
    conn.close()

    return {
        "reply":        ai_reply,
        "journal_saved": journal_saved
    }

if __name__ == "__main__":
    app.run(debug=True)