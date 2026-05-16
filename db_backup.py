# -*- coding: utf-8 -*-
"""
db_backup.py - Export your current Render PostgreSQL users table to a local SQL file.

Usage:
    python db_backup.py

This reads DATABASE_URL from your .env file and dumps all user data into:
    backups/backup_YYYYMMDD_HHMMSS.sql

Run this BEFORE your Render free DB expires (every ~90 days).
No need for pg_dump - uses Python/psycopg2 directly.
"""

import os
import sys
from datetime import datetime
from pathlib import Path
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    print("[ERROR] DATABASE_URL not found in your .env file.")
    sys.exit(1)

# Create backups folder if it doesn't exist
backup_dir = Path("backups")
backup_dir.mkdir(exist_ok=True)

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
backup_file = backup_dir / f"backup_{timestamp}.sql"

print(f"[BACKUP] Connecting to database...")
print(f"[SOURCE] {DATABASE_URL[:60]}...")

try:
    conn = psycopg2.connect(DATABASE_URL, sslmode="require")
    cur = conn.cursor()

    # Get all users
    cur.execute("SELECT id, email, password_hash, is_verified, total_uses, used_uses, created_at, last_login_at FROM users ORDER BY id ASC")
    rows = cur.fetchall()

    print(f"[INFO]   Found {len(rows)} users to backup.")

    with open(backup_file, "w", encoding="utf-8") as f:
        # Write header
        f.write(f"-- Database backup created at {datetime.now().isoformat()}\n")
        f.write(f"-- Source: {DATABASE_URL[:60]}...\n")
        f.write(f"-- Total users: {len(rows)}\n\n")

        # Write table creation (safe to run on empty or existing DB)
        f.write("CREATE TABLE IF NOT EXISTS users (\n")
        f.write("    id SERIAL PRIMARY KEY,\n")
        f.write("    email TEXT UNIQUE NOT NULL,\n")
        f.write("    password_hash TEXT,\n")
        f.write("    is_verified INTEGER NOT NULL DEFAULT 0,\n")
        f.write("    total_uses INTEGER NOT NULL DEFAULT 0,\n")
        f.write("    used_uses INTEGER NOT NULL DEFAULT 0,\n")
        f.write("    created_at TEXT NOT NULL DEFAULT '',\n")
        f.write("    last_login_at TEXT\n")
        f.write(");\n\n")

        # Write each user as an INSERT
        for row in rows:
            user_id, email, password_hash, is_verified, total_uses, used_uses, created_at, last_login_at = row

            # Safely escape single quotes in text fields
            def esc(val):
                if val is None:
                    return "NULL"
                return "'" + str(val).replace("'", "''") + "'"

            f.write(
                f"INSERT INTO users (email, password_hash, is_verified, total_uses, used_uses, created_at, last_login_at) "
                f"VALUES ({esc(email)}, {esc(password_hash)}, {is_verified}, {total_uses}, {used_uses}, {esc(created_at)}, {esc(last_login_at)}) "
                f"ON CONFLICT (email) DO UPDATE SET "
                f"password_hash = EXCLUDED.password_hash, "
                f"is_verified = EXCLUDED.is_verified, "
                f"total_uses = EXCLUDED.total_uses, "
                f"used_uses = EXCLUDED.used_uses, "
                f"created_at = EXCLUDED.created_at, "
                f"last_login_at = EXCLUDED.last_login_at;\n"
            )

        f.write(f"\n-- Backup complete: {len(rows)} users exported.\n")

    conn.close()

    size_kb = backup_file.stat().st_size / 1024
    print(f"[DONE]   Backup complete! {len(rows)} users saved.")
    print(f"[SAVED]  {backup_file.resolve()}")
    print(f"[SIZE]   {size_kb:.1f} KB")
    print()
    print("Next steps when you get a new Render DB:")
    print(f"  1. Create new DB on Render")
    print(f"  2. Update DATABASE_URL in your .env")
    print(f"  3. Run: python db_restore.py {backup_file}")

except psycopg2.OperationalError as e:
    print(f"[ERROR] Could not connect to database: {e}")
    sys.exit(1)
except Exception as e:
    print(f"[ERROR] {e}")
    sys.exit(1)
