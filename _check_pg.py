import os, json
from pymongo import MongoClient
url = os.environ.get("DATABASE_URL", "")
if not url:
    print("DATABASE_URL not set")
    exit(1)
client = MongoClient(url, serverSelectionTimeoutMS=5000)
db = client["kntu_bot"]
col = db["bot_store"]
doc = col.find_one({"_id": "main"})
data = doc.get("data", {}) if doc else {}
print("MongoDB data size:", len(json.dumps(data)))
w = data.get("wallets", {}).get("-1003766429228", {})
print("Wallets in main group:", len(w))
print("814851166 balance:", w.get("814851166", "NOT FOUND"))
print("Top keys:", list(data.keys()))
client.close()
