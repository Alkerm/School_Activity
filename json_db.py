"""
JSON-based user database for prototype use.
Stores all user data in a single JSON file with file-locking
to prevent corruption from concurrent writes.
"""

import json
import os
import threading
from datetime import datetime

_lock = threading.Lock()


class JsonDB:
    def __init__(self, path, default_trials=0):
        self.path = path
        self.default_trials = default_trials
        self._ensure_file()

    # ── internal helpers ──────────────────────────────────────

    def _ensure_file(self):
        """Create the JSON file with empty users list if it doesn't exist."""
        if not os.path.exists(self.path):
            db_dir = os.path.dirname(self.path)
            if db_dir:
                os.makedirs(db_dir, exist_ok=True)
            self._write({'next_id': 1, 'users': []})

    def _read(self):
        """Read and return the full database dict."""
        with open(self.path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def _write(self, data):
        """Atomically write the database dict to disk."""
        tmp_path = self.path + '.tmp'
        with open(tmp_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        # Atomic rename (works on Windows when target doesn't exist)
        if os.path.exists(self.path):
            os.replace(tmp_path, self.path)
        else:
            os.rename(tmp_path, self.path)

    @staticmethod
    def _user_dict(user):
        """Return a dict-like object that supports both dict['key'] and dict.get('key')."""
        return user

    # ── public API (same signatures as the old sqlite layer) ──

    def get_user_by_id(self, user_id):
        """Find a user by their integer ID."""
        with _lock:
            data = self._read()
        for user in data['users']:
            if user['id'] == user_id:
                return user
        return None

    def get_user_by_email(self, email):
        """Find a user by their email address."""
        with _lock:
            data = self._read()
        for user in data['users']:
            if user['email'] == email:
                return user
        return None

    def create_user(self, email, password_hash, now_iso):
        """Insert a new user and return the created user dict."""
        with _lock:
            data = self._read()
            # Double-check uniqueness inside lock
            for user in data['users']:
                if user['email'] == email:
                    return None  # already exists
            new_user = {
                'id': data['next_id'],
                'email': email,
                'password_hash': password_hash,
                'is_verified': 1,
                'total_uses': self.default_trials,
                'used_uses': 0,
                'created_at': now_iso,
                'last_login_at': now_iso,
            }
            data['next_id'] += 1
            data['users'].append(new_user)
            self._write(data)
        return new_user

    def update_login(self, user_id, now_iso):
        """Mark user as verified and update last_login_at. Returns updated user."""
        with _lock:
            data = self._read()
            for user in data['users']:
                if user['id'] == user_id:
                    user['is_verified'] = 1
                    user['last_login_at'] = now_iso
                    self._write(data)
                    return user
        return None

    def consume_one_use(self, user_id):
        """
        Decrement one use if available.
        Returns (success: bool, user: dict).
        """
        with _lock:
            data = self._read()
            for user in data['users']:
                if user['id'] == user_id:
                    if user['used_uses'] < user['total_uses']:
                        user['used_uses'] += 1
                        self._write(data)
                        return True, user
                    return False, user
        return False, None

    def refund_one_use(self, user_id):
        """Give back one use (e.g. after a failed prediction)."""
        with _lock:
            data = self._read()
            for user in data['users']:
                if user['id'] == user_id:
                    if user['used_uses'] > 0:
                        user['used_uses'] -= 1
                    self._write(data)
                    return
            # user not found – nothing to do

    def add_trials(self, user_id, additional_uses):
        """Add more trial uses to a user. Returns updated user."""
        with _lock:
            data = self._read()
            for user in data['users']:
                if user['id'] == user_id:
                    user['total_uses'] += additional_uses
                    self._write(data)
                    return user
        return None

    def list_users(self):
        """Return all users sorted by ID descending."""
        with _lock:
            data = self._read()
        return sorted(data['users'], key=lambda u: u['id'], reverse=True)
