import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
load_dotenv()

def get_connection():
    conn = psycopg2.connect(
        os.environ.get("DATABASE_URL"),
        cursor_factory=RealDictCursor
    )
    return conn

def init_db():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id       SERIAL PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS notes (
            id       SERIAL PRIMARY KEY,
            user_id  INTEGER NOT NULL REFERENCES users(id),
            title    TEXT NOT NULL,
            content  TEXT NOT NULL,
            created  TIMESTAMP DEFAULT NOW()
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS personas (
            id         SERIAL PRIMARY KEY,
            user_id    INTEGER UNIQUE NOT NULL REFERENCES users(id),
            goals      TEXT DEFAULT '',
            habits     TEXT DEFAULT '',
            summary    TEXT DEFAULT '',
            onboarded  BOOLEAN DEFAULT FALSE,
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS chats (
            id         SERIAL PRIMARY KEY,
            user_id    INTEGER NOT NULL REFERENCES users(id),
            role       TEXT NOT NULL,
            content    TEXT NOT NULL,
            created    TIMESTAMP DEFAULT NOW()
        )
    """)

    # Track which note is today's journal entry per user
    cur.execute("""
        CREATE TABLE IF NOT EXISTS daily_journals (
            id         SERIAL PRIMARY KEY,
            user_id    INTEGER NOT NULL REFERENCES users(id),
            note_id    INTEGER NOT NULL REFERENCES notes(id),
            date       DATE DEFAULT CURRENT_DATE,
            UNIQUE(user_id, date)
        )
    """)

    conn.commit()
    cur.close()
    conn.close()