import os
url = os.environ.get("DATABASE_URL", "")
if url:
    print(f"DB: SET ({url[:40]}...)")
else:
    print("DB: NOT_SET")
