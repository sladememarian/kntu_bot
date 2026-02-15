"""
Quick tool to inspect/edit the bot_store table in Railway PostgreSQL.

Usage:
  python _edit_db.py                     # Show all top-level keys and sizes
  python _edit_db.py get <key>           # Print a specific key's data
  python _edit_db.py delete <key>        # Delete a specific key
  python _edit_db.py set <key> <json>    # Set a key to a JSON value
  python _edit_db.py keys                # List all top-level keys
  python _edit_db.py raw                 # Dump entire data as JSON file
  python _edit_db.py load <file>         # Replace entire data from JSON file

You MUST set DATABASE_URL env var first:
  $env:DATABASE_URL = "postgresql://..."
"""

import sys
import json
import os

# Load .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

DB_URL = os.environ.get("DATABASE_URL", "")

# Strip quotes/spaces that may come from .env
DB_URL = DB_URL.strip().strip('"').strip("'")

if not DB_URL:
    print("ERROR: Set DATABASE_URL first!")
    print('  PowerShell:  $env:DATABASE_URL = "postgresql://user:pass@host:port/dbname"')
    print("  Get it from Railway → your PostgreSQL service → Variables → DATABASE_URL")
    sys.exit(1)

import psycopg2

def get_conn():
    return psycopg2.connect(DB_URL)

def load_data():
    conn = get_conn()
    with conn.cursor() as cur:
        cur.execute("SELECT data FROM bot_store WHERE id = 1;")
        row = cur.fetchone()
    conn.close()
    return row[0] if row else {}

def save_data(data):
    conn = get_conn()
    with conn.cursor() as cur:
        cur.execute("UPDATE bot_store SET data = %s WHERE id = 1;", (json.dumps(data, ensure_ascii=False),))
        conn.commit()
    conn.close()

def show_summary(data):
    print(f"\n{'='*60}")
    print(f"  bot_store — {len(data)} top-level keys")
    print(f"{'='*60}\n")
    for key in sorted(data.keys()):
        val = data[key]
        if isinstance(val, dict):
            size = len(val)
            desc = f"dict ({size} entries)"
        elif isinstance(val, list):
            size = len(val)
            desc = f"list ({size} items)"
        elif isinstance(val, bool):
            desc = f"bool = {val}"
        elif isinstance(val, (int, float)):
            desc = f"number = {val}"
        elif isinstance(val, str):
            desc = f'string = "{val[:50]}..."' if len(val) > 50 else f'string = "{val}"'
        else:
            desc = str(type(val).__name__)
        print(f"  {key:30s}  →  {desc}")
    print()

def main():
    args = sys.argv[1:]

    if not args:
        data = load_data()
        show_summary(data)
        return

    cmd = args[0].lower()

    if cmd == "keys":
        data = load_data()
        for k in sorted(data.keys()):
            print(k)

    elif cmd == "get":
        if len(args) < 2:
            print("Usage: python _edit_db.py get <key>")
            return
        key = args[1]
        data = load_data()
        val = data.get(key)
        if val is None:
            print(f"Key '{key}' not found.")
        else:
            print(json.dumps(val, ensure_ascii=False, indent=2))

    elif cmd == "delete":
        if len(args) < 2:
            print("Usage: python _edit_db.py delete <key>")
            return
        key = args[1]
        data = load_data()
        if key in data:
            del data[key]
            save_data(data)
            print(f"Deleted key '{key}'.")
        else:
            print(f"Key '{key}' not found.")

    elif cmd == "set":
        if len(args) < 3:
            print("Usage: python _edit_db.py set <key> <json_value>")
            return
        key = args[1]
        try:
            val = json.loads(args[2])
        except json.JSONDecodeError:
            val = args[2]  # Treat as string
        data = load_data()
        data[key] = val
        save_data(data)
        print(f"Set key '{key}' successfully.")

    elif cmd == "raw":
        data = load_data()
        out = "db_dump.json"
        with open(out, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"Dumped entire database to {out} ({len(data)} keys)")

    elif cmd == "load":
        if len(args) < 2:
            print("Usage: python _edit_db.py load <file.json>")
            return
        path = args[1]
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        save_data(data)
        print(f"Loaded {len(data)} keys from {path} into database.")

    else:
        print(__doc__)

if __name__ == "__main__":
    main()
