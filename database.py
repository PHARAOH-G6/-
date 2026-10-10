import sqlite3
from datetime import datetime
from pathlib import Path

# На Render можно смонтировать диск в /var/data — тогда данные сохранятся.
# На бесплатном плане диска нет, БД обнуляется при перезапуске.
DATA_DIR = Path("/var/data") if Path("/var/data").exists() else Path(".")
DB_PATH = DATA_DIR / "shifts.db"


def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS shifts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            username TEXT,
            fio TEXT,
            shift_date TEXT,
            shift_type TEXT,
            open_notes TEXT,
            incidents TEXT,
            powder TEXT,
            details TEXT,
            opened_at TEXT,
            closed_at TEXT,
            status TEXT DEFAULT 'open'
        )
    """)
    conn.commit()
    conn.close()


def get_open_shift(user_id: int):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "SELECT id, fio, shift_date, shift_type FROM shifts "
        "WHERE user_id=? AND status='open' ORDER BY id DESC LIMIT 1",
        (user_id,),
    )
    row = cur.fetchone()
    conn.close()
    return row


def create_shift(user_id, username, fio, shift_date, shift_type, open_notes):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO shifts (user_id, username, fio, shift_date, shift_type,
                            open_notes, opened_at, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, 'open')
    """, (user_id, username, fio, shift_date, shift_type, open_notes,
          datetime.now().isoformat(timespec="seconds")))
    conn.commit()
    shift_id = cur.lastrowid
    conn.close()
    return shift_id


def close_shift(user_id, incidents, powder, details):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        UPDATE shifts
        SET incidents=?, powder=?, details=?, closed_at=?, status='closed'
        WHERE user_id=? AND status='open'
    """, (incidents, powder, details,
          datetime.now().isoformat(timespec="seconds"), user_id))
    conn.commit()
    conn.close()


def get_last_closed_shift(user_id):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        SELECT fio, shift_date, shift_type, open_notes, incidents, powder,
               details, opened_at, closed_at
        FROM shifts
        WHERE user_id=? AND status='closed'
        ORDER BY id DESC LIMIT 1
    """, (user_id,))
    row = cur.fetchone()
    conn.close()
    return row
