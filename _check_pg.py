import os, json, psycopg2
c = psycopg2.connect(os.environ["DATABASE_URL"])
cur = c.cursor()
cur.execute("SELECT length(data::text) FROM bot_store WHERE id=1")
row = cur.fetchone()
print("PG data size:", row[0] if row else "NO DATA")
cur.execute("SELECT data FROM bot_store WHERE id=1")
row = cur.fetchone()
if row and row[0]:
    d = row[0] if isinstance(row[0], dict) else json.loads(row[0])
    w = d.get("wallets", {}).get("-1003766429228", {})
    print("Wallets in main group:", len(w))
    print("814851166 balance:", w.get("814851166", "NOT FOUND"))
    print("Top keys:", list(d.keys()))
else:
    print("NO DATA IN DB")
c.close()
