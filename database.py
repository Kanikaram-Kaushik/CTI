import sqlite3
import os
from datetime import datetime

if os.path.exists('/data'):
    DB_FILE = '/data/chat_history.db'
else:
    DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'chat_history.db')

def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def add_message(session_id, role, content):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute(
        'INSERT INTO messages (session_id, role, content, timestamp) VALUES (?, ?, ?, ?)',
        (session_id, role, content, datetime.now())
    )
    conn.commit()
    conn.close()

def get_chat_history(session_id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT role, content, timestamp FROM messages WHERE session_id = ? ORDER BY id ASC', (session_id,))
    rows = c.fetchall()
    conn.close()
    return [{"role": row["role"], "content": row["content"], "timestamp": row["timestamp"]} for row in rows]

def get_all_sessions():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT session_id, role, content, timestamp FROM messages ORDER BY id ASC')
    rows = c.fetchall()
    conn.close()
    sessions = {}
    for row in rows:
        sid = row["session_id"]
        if sid not in sessions:
            sessions[sid] = []
        sessions[sid].append({"role": row["role"], "content": row["content"], "timestamp": row["timestamp"]})
    return sessions

def clear_history():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('DELETE FROM messages')
    conn.commit()
    conn.close()

def delete_session(session_id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('DELETE FROM messages WHERE session_id = ?', (session_id,))
    conn.commit()
    conn.close()
