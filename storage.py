# ==========================================
# KNTU Bot 25 — Persistent Data Store (PostgreSQL + JSON fallback)
# ==========================================

import json
import os
import threading
import logging

logger = logging.getLogger("kntu_bot25.storage")

_DEFAULT_DATA_FILE = os.path.join(os.path.dirname(__file__), "data.json")
DATA_FILE = os.environ.get("DATA_FILE", _DEFAULT_DATA_FILE)
DATABASE_URL = os.environ.get("DATABASE_URL", "")

_lock = threading.Lock()

_DEFAULT = {
    "group_lang": {},
    "lagabs": {},
    "news_channels": {},
    "debug": False,
    "seen_members": {},
    "user_names": {},
}

# ---- Backend selector ----
_use_pg = False
_pg_pool = None


def _init_pg():
    """Initialize PostgreSQL connection pool and create tables."""
    global _use_pg, _pg_pool
    if not DATABASE_URL:
        logger.info("DATABASE_URL not set — using JSON file backend.")
        return
    try:
        import psycopg2
        import psycopg2.pool
        _pg_pool = psycopg2.pool.ThreadedConnectionPool(1, 5, DATABASE_URL)
        conn = _pg_pool.getconn()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS bot_store (
                        id   INTEGER PRIMARY KEY DEFAULT 1 CHECK (id = 1),
                        data JSONB NOT NULL DEFAULT '{}'::jsonb
                    );
                """)
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS markov_chain (
                        id    INTEGER PRIMARY KEY DEFAULT 1 CHECK (id = 1),
                        chain JSONB NOT NULL DEFAULT '{}'::jsonb
                    );
                """)
                cur.execute("""
                    INSERT INTO bot_store (id, data)
                    VALUES (1, '{}'::jsonb)
                    ON CONFLICT (id) DO NOTHING;
                """)
                cur.execute("""
                    INSERT INTO markov_chain (id, chain)
                    VALUES (1, '{}'::jsonb)
                    ON CONFLICT (id) DO NOTHING;
                """)
                conn.commit()
            _use_pg = True
            logger.info("PostgreSQL connection established.")
            _migrate_from_json(conn)
        finally:
            _pg_pool.putconn(conn)
    except Exception as e:
        logger.warning("PostgreSQL unavailable, falling back to JSON: %s", e)
        _use_pg = False


def _migrate_from_json(conn):
    """If DB data is empty and data.json exists, import it."""
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT data FROM bot_store WHERE id = 1;")
            row = cur.fetchone()
            db_data = row[0] if row else {}
            if db_data and any(k in db_data for k in
                               ("wallets", "group_lang", "seen_members", "lagabs")):
                logger.info("DB already has data — skipping migration.")
                return
            if not os.path.exists(DATA_FILE):
                return
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                file_data = json.load(f)
            if not file_data:
                return
            cur.execute(
                "UPDATE bot_store SET data = %s WHERE id = 1;",
                (json.dumps(file_data, ensure_ascii=False),)
            )
            conn.commit()
            logger.info("Migrated data.json (%d keys) into PostgreSQL.", len(file_data))
    except Exception as e:
        logger.warning("Migration from data.json failed: %s", e)


# ---- Core I/O ----

def _load_pg() -> dict:
    conn = _pg_pool.getconn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT data FROM bot_store WHERE id = 1;")
            row = cur.fetchone()
            return row[0] if row else dict(_DEFAULT)
    finally:
        _pg_pool.putconn(conn)


def _save_pg(data: dict):
    conn = _pg_pool.getconn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE bot_store SET data = %s WHERE id = 1;",
                (json.dumps(data, ensure_ascii=False),)
            )
            conn.commit()
    finally:
        _pg_pool.putconn(conn)


def _load_file() -> dict:
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return dict(_DEFAULT)


def _save_file(data: dict):
    parent_dir = os.path.dirname(DATA_FILE)
    if parent_dir:
        os.makedirs(parent_dir, exist_ok=True)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _load() -> dict:
    return _load_pg() if _use_pg else _load_file()


def _save(data: dict):
    if _use_pg:
        _save_pg(data)
    else:
        _save_file(data)


def load_data() -> dict:
    with _lock:
        return _load()


def save_data(data: dict):
    with _lock:
        _save(data)


# ---- Markov chain storage ----

def load_markov() -> dict:
    with _lock:
        if _use_pg:
            conn = _pg_pool.getconn()
            try:
                with conn.cursor() as cur:
                    cur.execute("SELECT chain FROM markov_chain WHERE id = 1;")
                    row = cur.fetchone()
                    return row[0] if row else {}
            finally:
                _pg_pool.putconn(conn)
        else:
            mf = os.path.join(os.path.dirname(DATA_FILE), "markov.json")
            if os.path.exists(mf):
                with open(mf, "r", encoding="utf-8") as f:
                    return json.load(f)
            return {}


def save_markov(chain: dict):
    with _lock:
        if _use_pg:
            conn = _pg_pool.getconn()
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        "UPDATE markov_chain SET chain = %s WHERE id = 1;",
                        (json.dumps(chain, ensure_ascii=False),)
                    )
                    conn.commit()
            finally:
                _pg_pool.putconn(conn)
        else:
            mf = os.path.join(os.path.dirname(DATA_FILE), "markov.json")
            with open(mf, "w", encoding="utf-8") as f:
                json.dump(chain, f, ensure_ascii=False)


# ---- Initialize on import ----
_init_pg()


# ===========================================================
# API FUNCTIONS (unchanged interface)
# ===========================================================

def get_lang(chat_id: int) -> str:
    data = load_data()
    return data.get("group_lang", {}).get(str(chat_id), "fa")


def set_lang(chat_id: int, lang: str):
    data = load_data()
    data.setdefault("group_lang", {})[str(chat_id)] = lang
    save_data(data)


def get_lagabs(chat_id: int) -> dict:
    data = load_data()
    return data.get("lagabs", {}).get(str(chat_id), {})


def set_lagab(chat_id: int, user_id: int, lagab: str):
    data = load_data()
    data.setdefault("lagabs", {}).setdefault(str(chat_id), {})[str(user_id)] = lagab
    save_data(data)


def get_news_channels(chat_id: int) -> list:
    data = load_data()
    return data.get("news_channels", {}).get(str(chat_id), [])


def add_news_channel(chat_id: int, channel: str):
    data = load_data()
    channels = data.setdefault("news_channels", {}).setdefault(str(chat_id), [])
    if channel not in channels:
        channels.append(channel)
    save_data(data)


def remove_news_channel(chat_id: int, channel: str):
    data = load_data()
    channels = data.get("news_channels", {}).get(str(chat_id), [])
    if channel in channels:
        channels.remove(channel)
    save_data(data)


def get_debug() -> bool:
    data = load_data()
    return data.get("debug", False)


def set_debug(val: bool):
    data = load_data()
    data["debug"] = val
    save_data(data)


def track_member(chat_id: int, user_id: int) -> bool:
    data = load_data()
    members = data.setdefault("seen_members", {}).setdefault(str(chat_id), [])
    if user_id not in members:
        members.append(user_id)
        save_data(data)
        return True
    return False


def get_members(chat_id: int) -> list:
    data = load_data()
    return data.get("seen_members", {}).get(str(chat_id), [])


def set_user_name(chat_id: int, user_id: int, name: str):
    data = load_data()
    names = data.setdefault("user_names", {}).setdefault(str(chat_id), {})
    names[str(user_id)] = name
    save_data(data)


def get_user_name(chat_id: int, user_id: int) -> str:
    data = load_data()
    return data.get("user_names", {}).get(str(chat_id), {}).get(str(user_id), "")


def add_warn(chat_id: int, user_id: int) -> int:
    data = load_data()
    warns = data.setdefault("warns", {}).setdefault(str(chat_id), {})
    current = warns.get(str(user_id), 0)
    current += 1
    warns[str(user_id)] = current
    save_data(data)
    return current


def get_warns(chat_id: int, user_id: int) -> int:
    data = load_data()
    return data.get("warns", {}).get(str(chat_id), {}).get(str(user_id), 0)


def reset_warns(chat_id: int, user_id: int):
    data = load_data()
    warns = data.get("warns", {}).get(str(chat_id), {})
    if str(user_id) in warns:
        del warns[str(user_id)]
        save_data(data)


# ---- Economy / Wallet ----

STARTING_BALANCE = 500


def get_balance(chat_id: int, user_id: int) -> int:
    data = load_data()
    return data.get("wallets", {}).get(str(chat_id), {}).get(str(user_id), STARTING_BALANCE)


def set_balance(chat_id: int, user_id: int, amount: int):
    data = load_data()
    wallets = data.setdefault("wallets", {}).setdefault(str(chat_id), {})
    wallets[str(user_id)] = max(0, amount)
    save_data(data)


def add_balance(chat_id: int, user_id: int, amount: int) -> int:
    bal = get_balance(chat_id, user_id)
    new_bal = max(0, bal + amount)
    set_balance(chat_id, user_id, new_bal)
    return new_bal


def get_all_balances(chat_id: int) -> dict:
    data = load_data()
    return data.get("wallets", {}).get(str(chat_id), {})


def get_daily_claim(chat_id: int, user_id: int) -> str:
    data = load_data()
    return data.get("daily_claims", {}).get(str(chat_id), {}).get(str(user_id), "")


def set_daily_claim(chat_id: int, user_id: int, date_str: str):
    data = load_data()
    claims = data.setdefault("daily_claims", {}).setdefault(str(chat_id), {})
    claims[str(user_id)] = date_str
    save_data(data)


# ---- Work / Spin cooldowns ----

def get_last_work(chat_id: int, user_id: int) -> str:
    data = load_data()
    return data.get("last_work", {}).get(str(chat_id), {}).get(str(user_id), "")


def set_last_work(chat_id: int, user_id: int, timestamp: str):
    data = load_data()
    works = data.setdefault("last_work", {}).setdefault(str(chat_id), {})
    works[str(user_id)] = timestamp
    save_data(data)


def get_last_spin(chat_id: int, user_id: int) -> str:
    data = load_data()
    return data.get("last_spin", {}).get(str(chat_id), {}).get(str(user_id), "")


def set_last_spin(chat_id: int, user_id: int, timestamp: str):
    data = load_data()
    spins = data.setdefault("last_spin", {}).setdefault(str(chat_id), {})
    spins[str(user_id)] = timestamp
    save_data(data)


# ---- Jail ----

def get_jail_time(chat_id: int, user_id: int) -> str:
    data = load_data()
    return data.get("jail", {}).get(str(chat_id), {}).get(str(user_id), "")


def set_jail_time(chat_id: int, user_id: int, timestamp: str):
    data = load_data()
    jail = data.setdefault("jail", {}).setdefault(str(chat_id), {})
    jail[str(user_id)] = timestamp
    save_data(data)


def clear_jail(chat_id: int, user_id: int):
    data = load_data()
    jail = data.get("jail", {}).get(str(chat_id), {})
    if str(user_id) in jail:
        del jail[str(user_id)]
        save_data(data)


# ---- Stocks / Investing ----

def get_stocks(chat_id: int, user_id: int) -> dict:
    data = load_data()
    return data.get("stocks", {}).get(str(chat_id), {}).get(str(user_id), {})


def set_stocks(chat_id: int, user_id: int, stocks: dict):
    data = load_data()
    s = data.setdefault("stocks", {}).setdefault(str(chat_id), {})
    s[str(user_id)] = stocks
    save_data(data)


# ---- Daily Events ----

def get_daily_event(chat_id: int) -> dict:
    data = load_data()
    return data.get("daily_events", {}).get(str(chat_id), {})


def set_daily_event(chat_id: int, event_data: dict):
    data = load_data()
    events = data.setdefault("daily_events", {})
    events[str(chat_id)] = event_data
    save_data(data)


# ---- Riddle daily limit ----

def get_riddle_count(chat_id: int, user_id: int) -> tuple[str, int]:
    data = load_data()
    entry = data.get("riddle_counts", {}).get(str(chat_id), {}).get(str(user_id), {})
    return entry.get("date", ""), entry.get("count", 0)


def inc_riddle_count(chat_id: int, user_id: int, today: str) -> int:
    data = load_data()
    rc = data.setdefault("riddle_counts", {}).setdefault(str(chat_id), {})
    entry = rc.get(str(user_id), {})
    if entry.get("date") != today:
        entry = {"date": today, "count": 0}
    entry["count"] += 1
    rc[str(user_id)] = entry
    save_data(data)
    return entry["count"]


# ---- Stock buy prices (for profit tracking) ----

def get_stock_costs(chat_id: int, user_id: int) -> dict:
    data = load_data()
    return data.get("stock_costs", {}).get(str(chat_id), {}).get(str(user_id), {})


def set_stock_costs(chat_id: int, user_id: int, costs: dict):
    data = load_data()
    sc = data.setdefault("stock_costs", {}).setdefault(str(chat_id), {})
    sc[str(user_id)] = costs
    save_data(data)


# ---- Inventory (shop items) ----

def get_inventory(chat_id: int, user_id: int) -> list:
    data = load_data()
    return data.get("inventory", {}).get(str(chat_id), {}).get(str(user_id), [])


def add_inventory_item(chat_id: int, user_id: int, item: dict):
    data = load_data()
    inv = data.setdefault("inventory", {}).setdefault(str(chat_id), {}).setdefault(str(user_id), [])
    inv.append(item)
    save_data(data)


def remove_inventory_item(chat_id: int, user_id: int, item_id: str) -> bool:
    data = load_data()
    inv = data.get("inventory", {}).get(str(chat_id), {}).get(str(user_id), [])
    for i, it in enumerate(inv):
        if it.get("item_id") == item_id:
            inv.pop(i)
            save_data(data)
            return True
    return False


def has_item(chat_id: int, user_id: int, item_id: str) -> bool:
    inv = get_inventory(chat_id, user_id)
    return any(it.get("item_id") == item_id for it in inv)


# ---- Jail list helpers ----

def get_all_jailed(chat_id: int) -> dict:
    data = load_data()
    return data.get("jail", {}).get(str(chat_id), {})


# ---- Purchase tracking (for inflation / supply-demand) ----

def get_purchase_counts(chat_id: int) -> dict:
    """Returns {item_id: count} for a chat's purchase history."""
    data = load_data()
    return data.get("purchase_counts", {}).get(str(chat_id), {})


def record_purchase(chat_id: int, item_id: str, qty: int = 1):
    """Increment the purchase counter for an item in this chat."""
    data = load_data()
    pc = data.setdefault("purchase_counts", {}).setdefault(str(chat_id), {})
    pc[item_id] = pc.get(item_id, 0) + qty
    save_data(data)


# ---- Charity / Donations ----

def add_donation(chat_id: int, user_id: int, amount: int):
    """Add a donation amount for a user in this chat."""
    data = load_data()
    don = data.setdefault("donations", {}).setdefault(str(chat_id), {})
    don[str(user_id)] = don.get(str(user_id), 0) + amount
    save_data(data)


def get_donations(chat_id: int) -> dict:
    """Returns {user_id_str: total_donated} for a chat."""
    data = load_data()
    return data.get("donations", {}).get(str(chat_id), {})


# ---- Real Estate ----

def get_properties(chat_id: int, user_id: int) -> list:
    """Returns list of property dicts owned by a user."""
    data = load_data()
    return data.get("properties", {}).get(str(chat_id), {}).get(str(user_id), [])


def add_property(chat_id: int, user_id: int, prop: dict):
    """Add a property to user's portfolio."""
    data = load_data()
    props = data.setdefault("properties", {}).setdefault(str(chat_id), {}).setdefault(str(user_id), [])
    props.append(prop)
    save_data(data)


def remove_property(chat_id: int, user_id: int, prop_id: str) -> bool:
    """Remove a property by its ID. Returns True if found and removed."""
    data = load_data()
    props = data.get("properties", {}).get(str(chat_id), {}).get(str(user_id), [])
    for i, p in enumerate(props):
        if p.get("id") == prop_id:
            props.pop(i)
            save_data(data)
            return True
    return False


def get_all_properties(chat_id: int) -> dict:
    """Returns {user_id_str: [properties]} for a chat."""
    data = load_data()
    return data.get("properties", {}).get(str(chat_id), {})


# ── Daily streak ───────────────────────────────────────────
def get_daily_streak(chat_id: int, user_id: int) -> dict:
    data = load_data()
    return data.get("daily_streaks", {}).get(str(chat_id), {}).get(str(user_id), {"count": 0, "last": ""})

def set_daily_streak(chat_id: int, user_id: int, streak: dict):
    data = load_data()
    cid, uid = str(chat_id), str(user_id)
    data.setdefault("daily_streaks", {}).setdefault(cid, {})[uid] = streak
    save_data(data)


# ── Work XP ────────────────────────────────────────────────
def get_work_xp(chat_id: int, user_id: int) -> int:
    data = load_data()
    return data.get("work_xp", {}).get(str(chat_id), {}).get(str(user_id), 0)

def add_work_xp(chat_id: int, user_id: int, amount: int = 1) -> int:
    data = load_data()
    cid, uid = str(chat_id), str(user_id)
    xp = data.setdefault("work_xp", {}).setdefault(cid, {}).get(uid, 0)
    xp += amount
    data["work_xp"][cid][uid] = xp
    save_data(data)
    return xp
