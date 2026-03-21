"""
PostgreSQL user database for production use.
Same interface as json_db.py so app.py works with either backend.
Requires DATABASE_URL environment variable.
"""

import psycopg2
import psycopg2.extras
import os


class PostgresDB:
    def __init__(self, database_url, default_trials=0):
        self.database_url = database_url
        self.default_trials = default_trials
        self._init_table()

    # ── internal helpers ──────────────────────────────────────

    def _get_conn(self):
        """Create a new connection to the database."""
        conn = psycopg2.connect(self.database_url)
        conn.autocommit = False
        return conn

    def _init_table(self):
        """Create the users table if it doesn't exist."""
        conn = self._get_conn()
        try:
            cur = conn.cursor()
            cur.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    email TEXT UNIQUE NOT NULL,
                    password_hash TEXT,
                    is_verified INTEGER NOT NULL DEFAULT 0,
                    total_uses INTEGER NOT NULL DEFAULT 0,
                    used_uses INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL DEFAULT '',
                    last_login_at TEXT
                )
            ''')
            conn.commit()
        finally:
            conn.close()

    @staticmethod
    def _row_to_dict(cur, row):
        """Convert a psycopg2 row to a regular dict."""
        if row is None:
            return None
        columns = [desc[0] for desc in cur.description]
        return dict(zip(columns, row))

    # ── public API (same signatures as json_db.JsonDB) ────────

    def get_user_by_id(self, user_id):
        """Find a user by their integer ID."""
        conn = self._get_conn()
        try:
            cur = conn.cursor()
            cur.execute('SELECT * FROM users WHERE id = %s', (user_id,))
            return self._row_to_dict(cur, cur.fetchone())
        finally:
            conn.close()

    def get_user_by_email(self, email):
        """Find a user by their email address."""
        conn = self._get_conn()
        try:
            cur = conn.cursor()
            cur.execute('SELECT * FROM users WHERE email = %s', (email,))
            return self._row_to_dict(cur, cur.fetchone())
        finally:
            conn.close()

    def create_user(self, email, password_hash, now_iso):
        """Insert a new user and return the created user dict."""
        conn = self._get_conn()
        try:
            cur = conn.cursor()
            cur.execute(
                '''
                INSERT INTO users (email, password_hash, is_verified, total_uses, used_uses, created_at, last_login_at)
                VALUES (%s, %s, 1, %s, 0, %s, %s)
                RETURNING *
                ''',
                (email, password_hash, self.default_trials, now_iso, now_iso)
            )
            user = self._row_to_dict(cur, cur.fetchone())
            conn.commit()
            return user
        except psycopg2.IntegrityError:
            conn.rollback()
            return None  # email already exists
        finally:
            conn.close()

    def update_login(self, user_id, now_iso):
        """Mark user as verified and update last_login_at. Returns updated user."""
        conn = self._get_conn()
        try:
            cur = conn.cursor()
            cur.execute(
                '''
                UPDATE users SET is_verified = 1, last_login_at = %s
                WHERE id = %s
                RETURNING *
                ''',
                (now_iso, user_id)
            )
            user = self._row_to_dict(cur, cur.fetchone())
            conn.commit()
            return user
        finally:
            conn.close()

    def consume_one_use(self, user_id):
        """
        Decrement one use if available.
        Returns (success: bool, user: dict).
        """
        conn = self._get_conn()
        try:
            cur = conn.cursor()
            cur.execute(
                '''
                UPDATE users
                SET used_uses = used_uses + 1
                WHERE id = %s AND used_uses < total_uses
                RETURNING *
                ''',
                (user_id,)
            )
            row = cur.fetchone()
            if row:
                conn.commit()
                return True, self._row_to_dict(cur, row)
            else:
                conn.rollback()
                # Return current user state
                cur.execute('SELECT * FROM users WHERE id = %s', (user_id,))
                return False, self._row_to_dict(cur, cur.fetchone())
        finally:
            conn.close()

    def refund_one_use(self, user_id):
        """Give back one use (e.g. after a failed prediction)."""
        conn = self._get_conn()
        try:
            cur = conn.cursor()
            cur.execute(
                '''
                UPDATE users
                SET used_uses = CASE WHEN used_uses > 0 THEN used_uses - 1 ELSE 0 END
                WHERE id = %s
                ''',
                (user_id,)
            )
            conn.commit()
        finally:
            conn.close()

    def add_trials(self, user_id, additional_uses):
        """Add more trial uses to a user. Returns updated user."""
        conn = self._get_conn()
        try:
            cur = conn.cursor()
            cur.execute(
                '''
                UPDATE users SET total_uses = total_uses + %s
                WHERE id = %s
                RETURNING *
                ''',
                (additional_uses, user_id)
            )
            user = self._row_to_dict(cur, cur.fetchone())
            conn.commit()
            return user
        finally:
            conn.close()

    def list_users(self):
        """Return all users sorted by ID descending."""
        conn = self._get_conn()
        try:
            cur = conn.cursor()
            cur.execute(
                'SELECT id, email, used_uses, total_uses, created_at, last_login_at FROM users ORDER BY id DESC'
            )
            columns = [desc[0] for desc in cur.description]
            return [dict(zip(columns, row)) for row in cur.fetchall()]
        finally:
            conn.close()
