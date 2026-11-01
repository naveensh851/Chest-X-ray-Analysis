"""
Interactive SQLite Shell for xray_app.db
Run:
    python backend/sqlite_shell.py
"""
import sqlite3
import sys
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "xray_app.db"

def main():
    if not DB_PATH.exists():
        print(f"Database file not found: {DB_PATH}")
        sys.exit(1)

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    print("=" * 65)
    print(f"Connected to SQLite Database: {DB_PATH.name}")
    print("Type your SQL query (e.g. 'SELECT id, email FROM users;')")
    print("Commands:")
    print("  .tables   - List all tables")
    print("  .schema   - View table schema")
    print("  exit/quit - Quit shell")
    print("=" * 65)

    while True:
        try:
            query = input("sqlite> ").strip()
            if not query:
                continue
            if query.lower() in ("exit", "quit", ".exit", ".quit"):
                print("Bye.")
                break
            if query == ".tables":
                cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
                tables = [r[0] for r in cur.fetchall()]
                print("  ".join(tables))
                continue
            if query.startswith(".schema"):
                cur.execute("SELECT sql FROM sqlite_master WHERE type='table';")
                for r in cur.fetchall():
                    print(r[0] + ";\n")
                continue

            cur.execute(query)
            if query.strip().upper().startswith(("SELECT", "PRAGMA")):
                rows = cur.fetchall()
                if not rows:
                    print("(0 rows returned)")
                else:
                    col_names = [desc[0] for desc in cur.description]
                    print(" | ".join(col_names))
                    print("-" * (len(" | ".join(col_names)) + 5))
                    for row in rows:
                        print(" | ".join(str(val) for val in row))
                    print(f"({len(rows)} row(s))")
            else:
                conn.commit()
                print("Query executed successfully.")
        except KeyboardInterrupt:
            print("\nBye.")
            break
        except Exception as e:
            print(f"Error: {e}")

    conn.close()

if __name__ == "__main__":
    main()
