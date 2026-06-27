"""Push local data.json into MongoDB bot_store collection."""
import os, sys, json

DB_URL = os.environ.get("DATABASE_URL", "")
if not DB_URL:
    print("ERROR: DATABASE_URL not set")
    sys.exit(1)

# Read JSON from stdin
raw = sys.stdin.read()
data = json.loads(raw)
print(f"Loaded {len(data)} keys from stdin")

from pymongo import MongoClient
client = MongoClient(DB_URL, serverSelectionTimeoutMS=5000)
db = client["kntu_bot"]
col = db["bot_store"]
col.update_one({"_id": "main"}, {"$set": {"data": data}}, upsert=True)
doc = col.find_one({"_id": "main"})
size = len(json.dumps(doc.get("data", {})))
client.close()
print(f"SUCCESS: Wrote {size} chars to MongoDB bot_store")
