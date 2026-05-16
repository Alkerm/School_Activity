# -*- coding: utf-8 -*-
"""
db_restore.py - Import a backup SQL file into a new Render PostgreSQL database.

Usage:
    python db_restore.py backups/backup_YYYYMMDD_HHMMSS.sql

Steps to migrate to a new Render DB:
    1. Create a new PostgreSQL database on Render
    2. Copy the new External Database URL from Render dashboard
    3. Update DATABASE_URL in your .env file with the new URL
    4. Also update DATABASE_URL in Vercel -> Project -> Settings -> Environment Variables
    5. Run: python db_restore.py backups/your_backup_file.sql
    6. Redeploy on Vercel (Trigger Deployment button)

No need for psql CLI - uses Python/psycopg2 directly.
"""

import os
import sys
from pathlib import Path
import psycopg2
from dotenv import load_dotenv

load_dotenv()

# ── Argument check ────────────────────────────────────────────────────────────
if len(sys.argv) < 2:
    backup_dir = Path("backups")
    if backup_dir.exists():
        backups = sorted(backup_dir.glob("*.sql"), reverse=True)
        if backups:
            print("Available backups:")
            for b in backups:
                size_kb = b.stat().st_size / 1024
                print(f"  {b}  ({size_kb:.1f} KB)")
            print()
            print(f"Usage: python db_restore.py {backups[0]}")
        else:
            print("No backups found in ./backups/")
            print("Run: python db_backup.py first.")
    else:
        print("Usage: python db_restore.py <backup_file.sql>")
    sys.exit(1)

backup_file = Path(sys.argv[1])

if not backup_file.exists():
    print(f"[ERROR] File not found: {backup_file}")
    sys.exit(1)

# ── Read target DB URL ────────────────────────────────────────────────────────
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    print("[ERROR] DATABASE_URL not found in your .env file.")
    print("  Update .env with your NEW Render database URL first.")
    sys.exit(1)

# ── Safety confirmation ───────────────────────────────────────────────────────
size_kb = backup_file.stat().st_size / 1024
print(f"[FILE]   {backup_file} ({size_kb:.1f} KB)")
print(f"[TARGET] {DATABASE_URL[:60]}...")
print()
confirm = input("[WARNING] This will import data into the TARGET database. Continue? (yes/no): ").strip().lower()

if confirm != "yes":
    print("Cancelled.")
    sys.exit(0)

# ── Restore ───────────────────────────────────────────────────────────────────
print(f"\n[RESTORE] Connecting to target database...")

try:
    conn = psycopg2.connect(DATABASE_URL, sslmode="require")
    conn.autocommit = False
    cur = conn.cursor()

    print(f"[RESTORE] Running SQL from {backup_file}...")

    sql_content = backup_file.read_text(encoding="utf-8")

    # Split statements on semicolons and execute each one
    statements = [s.strip() for s in sql_content.split(";") if s.strip() and not s.strip().startswith("--")]

    success = 0
    skipped = 0
    for stmt in statements:
        if not stmt:
            continue
        try:
            cur.execute(stmt)
            success += 1
        except psycopg2.Error as e:
            print(f"  [SKIP] {e.pgerror or str(e)[:100]}")
            conn.rollback()
            skipped += 1
            # Re-open cursor after rollback
            cur = conn.cursor()

    conn.commit()
    conn.close()

    print(f"\n[DONE]   Restore complete!")
    print(f"  Statements executed: {success}")
    if skipped:
        print(f"  Skipped (already exist / harmless): {skipped}")
    print()
    print("Next steps:")
    print("  1. Go to Vercel -> Project -> Settings -> Environment Variables")
    print("  2. Update DATABASE_URL to your new Render DB URL")
    print("  3. Click 'Redeploy' in Vercel")

except psycopg2.OperationalError as e:
    print(f"[ERROR] Could not connect to database: {e}")
    sys.exit(1)
except Exception as e:
    print(f"[ERROR] {e}")
    sys.exit(1)
