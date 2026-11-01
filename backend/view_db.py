"""
SQLite Database Viewer CLI for AI Chest X-ray App
Usage:
    python backend/view_db.py
"""
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "xray_app.db"

def inspect_db():
    if not DB_PATH.exists():
        print(f"Database not found at: {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    print("=" * 60)
    print("                SQLITE DATABASE: xray_app.db")
    print("=" * 60)

    # 1. Users Table
    print("\n[1] USERS TABLE (Accounts & Emails):")
    print("-" * 60)
    print(f"{'User ID':<10} | {'Email Address'}")
    print("-" * 60)
    cur.execute("SELECT id, email FROM users ORDER BY id ASC")
    users = cur.fetchall()
    for uid, email in users:
        print(f"{uid:<10} | {email}")
    print(f"Total Users: {len(users)}")

    # 2. Reports Table
    print("\n[2] REPORTS TABLE (Diagnoses & Scans):")
    print("-" * 75)
    print(f"{'Report ID':<10} | {'User ID':<8} | {'Disease':<15} | {'Confidence':<10} | {'Created At'}")
    print("-" * 75)
    cur.execute("SELECT id, user_id, disease, confidence, created_at FROM reports ORDER BY id ASC")
    reports = cur.fetchall()
    for rid, uid, disease, conf, created in reports:
        print(f"{rid:<10} | {uid:<8} | {disease:<15} | {conf:<10.2f} | {created}")
    print(f"Total Reports: {len(reports)}")
    print("=" * 75)

    conn.close()

if __name__ == "__main__":
    inspect_db()
