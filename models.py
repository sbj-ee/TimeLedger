import sqlite3
from datetime import date, datetime, timedelta
from pathlib import Path

DB_PATH = Path(__file__).parent / "timeledger.db"


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            description TEXT DEFAULT '',
            active INTEGER DEFAULT 1,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            hours REAL NOT NULL,
            note TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (project_id) REFERENCES projects(id)
        );

        CREATE TABLE IF NOT EXISTS timers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            started_at TEXT NOT NULL,
            FOREIGN KEY (project_id) REFERENCES projects(id)
        );

        CREATE INDEX IF NOT EXISTS idx_entries_date ON entries(date);
        CREATE INDEX IF NOT EXISTS idx_entries_project ON entries(project_id);
    """)
    conn.commit()
    conn.close()


# --- Projects ---

def get_projects(active_only=True):
    conn = get_db()
    if active_only:
        rows = conn.execute(
            "SELECT * FROM projects WHERE active = 1 ORDER BY name"
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM projects ORDER BY active DESC, name").fetchall()
    conn.close()
    return rows


def get_project(project_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
    conn.close()
    return row


def create_project(name, description=""):
    conn = get_db()
    conn.execute(
        "INSERT INTO projects (name, description) VALUES (?, ?)",
        (name, description),
    )
    conn.commit()
    conn.close()


def update_project(project_id, name, description, active):
    conn = get_db()
    conn.execute(
        "UPDATE projects SET name = ?, description = ?, active = ? WHERE id = ?",
        (name, description, active, project_id),
    )
    conn.commit()
    conn.close()


# --- Entries ---

def get_entries(project_id=None, start_date=None, end_date=None, limit=None):
    conn = get_db()
    query = """
        SELECT e.*, p.name as project_name
        FROM entries e
        JOIN projects p ON e.project_id = p.id
        WHERE 1=1
    """
    params = []

    if project_id:
        query += " AND e.project_id = ?"
        params.append(project_id)
    if start_date:
        query += " AND e.date >= ?"
        params.append(start_date)
    if end_date:
        query += " AND e.date <= ?"
        params.append(end_date)

    query += " ORDER BY e.date DESC, e.created_at DESC"

    if limit:
        query += " LIMIT ?"
        params.append(limit)

    rows = conn.execute(query, params).fetchall()
    conn.close()
    return rows


def get_entry(entry_id):
    conn = get_db()
    row = conn.execute(
        "SELECT e.*, p.name as project_name FROM entries e JOIN projects p ON e.project_id = p.id WHERE e.id = ?",
        (entry_id,),
    ).fetchone()
    conn.close()
    return row


def create_entry(project_id, entry_date, hours, note=""):
    conn = get_db()
    conn.execute(
        "INSERT INTO entries (project_id, date, hours, note) VALUES (?, ?, ?, ?)",
        (project_id, entry_date, hours, note),
    )
    conn.commit()
    conn.close()


def update_entry(entry_id, project_id, entry_date, hours, note):
    conn = get_db()
    conn.execute(
        "UPDATE entries SET project_id = ?, date = ?, hours = ?, note = ? WHERE id = ?",
        (project_id, entry_date, hours, note, entry_id),
    )
    conn.commit()
    conn.close()


def delete_entry(entry_id):
    conn = get_db()
    conn.execute("DELETE FROM entries WHERE id = ?", (entry_id,))
    conn.commit()
    conn.close()


# --- Timers ---

def get_active_timer():
    conn = get_db()
    row = conn.execute(
        "SELECT t.*, p.name as project_name FROM timers t JOIN projects p ON t.project_id = p.id LIMIT 1"
    ).fetchone()
    conn.close()
    return row


def start_timer(project_id):
    conn = get_db()
    conn.execute("DELETE FROM timers")
    conn.execute(
        "INSERT INTO timers (project_id, started_at) VALUES (?, ?)",
        (project_id, datetime.now().isoformat()),
    )
    conn.commit()
    conn.close()


def stop_timer():
    timer = get_active_timer()
    if not timer:
        return None

    started = datetime.fromisoformat(timer["started_at"])
    elapsed = datetime.now() - started
    hours = round(elapsed.total_seconds() / 3600, 2)

    create_entry(timer["project_id"], date.today().isoformat(), hours)

    conn = get_db()
    conn.execute("DELETE FROM timers")
    conn.commit()
    conn.close()
    return hours


def cancel_timer():
    conn = get_db()
    conn.execute("DELETE FROM timers")
    conn.commit()
    conn.close()


# --- Summaries ---

def get_summary(start_date, end_date):
    conn = get_db()
    rows = conn.execute(
        """
        SELECT p.name as project_name, SUM(e.hours) as total_hours, COUNT(e.id) as entry_count
        FROM entries e
        JOIN projects p ON e.project_id = p.id
        WHERE e.date >= ? AND e.date <= ?
        GROUP BY p.name
        ORDER BY total_hours DESC
        """,
        (start_date, end_date),
    ).fetchall()
    conn.close()
    return rows


def get_daily_totals(start_date, end_date):
    conn = get_db()
    rows = conn.execute(
        """
        SELECT e.date, SUM(e.hours) as total_hours
        FROM entries e
        WHERE e.date >= ? AND e.date <= ?
        GROUP BY e.date
        ORDER BY e.date
        """,
        (start_date, end_date),
    ).fetchall()
    conn.close()
    return rows
