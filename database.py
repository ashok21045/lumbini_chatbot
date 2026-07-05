"""
database.py
------------
Step 3: SQLite database layer.

Tables:
  admin            -> name, contact_detail, email, password (hashed), address
                       Only rows that exist here can log in. There is NO public
                       "sign up and get instant access" flow for the chatbot -
                       new admins are added via add_admin() (e.g. run once from
                       a Python shell, or exposed to a super-admin only).
  conversations     -> stores chat history per logged-in admin (Step 5)

Password security:
  Passwords are never stored in plain text. We salt + SHA-256 hash them.

Email validation:
  Uses the regex pattern requested: contains "@" with a proper domain, e.g.
      ^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+[dot][a-zA-Z]{2,}$   (dot = literal '.')
"""

import sqlite3
import hashlib
import hmac
import os
import re
import json
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "app.db")

EMAIL_REGEX = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"


def is_valid_email(email: str) -> bool:
    return bool(re.match(EMAIL_REGEX, email or ""))


def _get_conn():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS admin (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            name            TEXT NOT NULL,
            contact_detail  TEXT NOT NULL,
            email           TEXT NOT NULL UNIQUE,
            password_hash   TEXT NOT NULL,
            salt            TEXT NOT NULL,
            address         TEXT NOT NULL,
            created_at      TEXT NOT NULL
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS conversations (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            admin_email TEXT NOT NULL,
            role        TEXT NOT NULL,      -- 'user' or 'bot'
            message     TEXT NOT NULL,
            timestamp   TEXT NOT NULL,
            FOREIGN KEY (admin_email) REFERENCES admin(email)
        )
        """
    )
    conn.commit()
    conn.close()


def _hash_password(password: str, salt: str = None):
    if salt is None:
        salt = os.urandom(16).hex()
    pwd_hash = hashlib.sha256((salt + password).encode("utf-8")).hexdigest()
    return pwd_hash, salt


def add_admin(name: str, contact_detail: str, email: str, password: str, address: str) -> tuple:
    """Register a new admin. Returns (success: bool, message: str)."""
    if not is_valid_email(email):
        return False, "Invalid email format."
    if not name or not contact_detail or not password or not address:
        return False, "All fields are required."
    if len(password) < 6:
        return False, "Password must be at least 6 characters."

    pwd_hash, salt = _hash_password(password)
    conn = _get_conn()
    try:
        conn.execute(
            """INSERT INTO admin (name, contact_detail, email, password_hash, salt, address, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (name, contact_detail, email.lower().strip(), pwd_hash, salt, address, datetime.now().isoformat()),
        )
        conn.commit()
        return True, "Admin registered successfully."
    except sqlite3.IntegrityError:
        return False, "An account with this email already exists."
    finally:
        conn.close()


def verify_login(email: str, password: str) -> tuple:
    """Check credentials against the admin table.
    Only someone whose info already exists in the DB can log in.
    Returns (success: bool, admin_row_or_none, message: str)
    """
    if not is_valid_email(email):
        return False, None, "Invalid email format."

    conn = _get_conn()
    row = conn.execute(
        "SELECT * FROM admin WHERE email = ?", (email.lower().strip(),)
    ).fetchone()
    conn.close()

    if row is None:
        return False, None, "No account found with that email."

    computed_hash, _ = _hash_password(password, row["salt"])
    if hmac.compare_digest(computed_hash, row["password_hash"]):
        return True, dict(row), "Login successful."
    return False, None, "Incorrect password."


def save_message(admin_email: str, role: str, message: str):
    conn = _get_conn()
    conn.execute(
        "INSERT INTO conversations (admin_email, role, message, timestamp) VALUES (?, ?, ?, ?)",
        (admin_email, role, message, datetime.now().isoformat()),
    )
    conn.commit()
    conn.close()


def get_history(admin_email: str, limit: int = 200):
    conn = _get_conn()
    rows = conn.execute(
        "SELECT role, message, timestamp FROM conversations WHERE admin_email = ? "
        "ORDER BY id ASC LIMIT ?",
        (admin_email, limit),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def clear_history(admin_email: str):
    conn = _get_conn()
    conn.execute("DELETE FROM conversations WHERE admin_email = ?", (admin_email,))
    conn.commit()
    conn.close()


def seed_default_admin():
    """Convenience helper: creates a default admin (admin@lict.edu.np / admin123)
    ONLY if the admin table is empty, so you have something to log in with
    the first time you run the app."""
    conn = _get_conn()
    count = conn.execute("SELECT COUNT(*) as c FROM admin").fetchone()["c"]
    conn.close()
    if count == 0:
        add_admin(
            name="Default Admin",
            contact_detail="9800000000",
            email="admin@lict.edu.np",
            password="admin123",
            address="Gaindakot-4, Kaligandaki Chowk, Nepal",
        )
        print("Seeded default admin -> email: admin@lict.edu.np | password: admin123")


if __name__ == "__main__":
    init_db()
    seed_default_admin()
    print(f"Database initialized at {DB_PATH}")
