"""Push local data.json into PostgreSQL bot_store table."""
import os, sys, json

DB_URL = os.environ.get("DATABASE_URL", "")
if not DB_URL:
    print("ERROR: DATABASE_URL not set")
    sys.exit(1)

# Read JSON from stdin
raw = sys.stdin.read()
data = json.loads(raw)
print(f"Loaded {len(data)} keys from stdin")

import psycopg2
conn = psycopg2.connect(DB_URL)
cur = conn.cursor()
cur.execute("UPDATE bot_store SET data = %s WHERE id = 1;", (json.dumps(data, ensure_ascii=False),))
conn.commit()
cur.execute("SELECT length(data::text) FROM bot_store WHERE id = 1;")
size = cur.fetchone()[0]
cur.close()
conn.close()
print(f"SUCCESS: Wrote {size} chars to PostgreSQL bot_store")
