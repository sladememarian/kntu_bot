# ==========================================
# KNTU Bot 25 — Persistent Data Store (MongoDB + JSON fallback)
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
_use_mongo = False
_mongo_client = None
_mongo_db = None


def _init_mongo():
    """Initialize MongoDB connection."""
    global _use_mongo, _mongo_client, _mongo_db
    if not DATABASE_URL:
        logger.info("DATABASE_URL not set — using JSON file backend.")
        return
    try:
        from pymongo import MongoClient
        _mongo_client = MongoClient(DATABASE_URL, serverSelectionTimeoutMS=5000)
        _mongo_client.admin.command("ping")
        _mongo_db = _mongo_client["kntu_bot"]
        _use_mongo = True
        logger.info("MongoDB connection established.")
        _migrate_from_json()
    except Exception as e:
        logger.warning("MongoDB unavailable, falling back to JSON: %s", e)
        _use_mongo = False


def _migrate_from_json():
    """If DB data is empty and data.json exists, import it."""
    try:
        col = _mongo_db["bot_store"]
        doc = col.find_one({"_id": "main"})
        if doc and doc.get("data"):
            db_data = doc["data"]
            if any(k in db_data for k in ("wallets", "group_lang", "seen_members", "lagabs")):
                logger.info("DB already has data — skipping migration.")
                return
        if not os.path.exists(DATA_FILE):
            return
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            file_data = json.load(f)
        if not file_data:
            return
        col.update_one(
            {"_id": "main"},
            {"$set": {"data": file_data}},
            upsert=True,
        )
        logger.info("Migrated data.json (%d keys) into MongoDB.", len(file_data))
    except Exception as e:
        logger.warning("Migration from data.json failed: %s", e)


# ---- Core I/O ----

def _load_mongo() -> dict:
    doc = _mongo_db["bot_store"].find_one({"_id": "main"})
    if doc and "data" in doc:
        return doc["data"]
    return dict(_DEFAULT)


def _save_mongo(data: dict):
    _mongo_db["bot_store"].update_one(
        {"_id": "main"},
        {"$set": {"data": data}},
        upsert=True,
    )


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
    return _load_mongo() if _use_mongo else _load_file()


def _save(data: dict):
    if _use_mongo:
        _save_mongo(data)
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
        if _use_mongo:
            doc = _mongo_db["markov_chain"].find_one({"_id": "main"})
            if doc and "chain" in doc:
                return doc["chain"]
            return {}
        else:
            mf = os.path.join(os.path.dirname(DATA_FILE), "markov.json")
            if os.path.exists(mf):
                with open(mf, "r", encoding="utf-8") as f:
                    return json.load(f)
            return {}


def save_markov(chain: dict):
    with _lock:
        if _use_mongo:
            _mongo_db["markov_chain"].update_one(
                {"_id": "main"},
                {"$set": {"chain": chain}},
                upsert=True,
            )
        else:
            mf = os.path.join(os.path.dirname(DATA_FILE), "markov.json")
            with open(mf, "w", encoding="utf-8") as f:
                json.dump(chain, f, ensure_ascii=False)


# ---- Initialize on import ----
_init_mongo()


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


# ── Gacha collections ─────────────────────────────────────
def get_gacha_collection(chat_id: int, user_id: int) -> list:
    data = load_data()
    return data.get("gacha_collections", {}).get(str(chat_id), {}).get(str(user_id), [])

def add_gacha_character(chat_id: int, user_id: int, char: dict):
    data = load_data()
    col = data.setdefault("gacha_collections", {}).setdefault(str(chat_id), {}).setdefault(str(user_id), [])
    col.append(char)
    save_data(data)

def remove_gacha_character(chat_id: int, user_id: int, char_id: str) -> bool:
    data = load_data()
    col = data.get("gacha_collections", {}).get(str(chat_id), {}).get(str(user_id), [])
    for i, c in enumerate(col):
        if c.get("id") == char_id:
            col.pop(i)
            save_data(data)
            return True
    return False

def get_claimed_characters(chat_id: int) -> dict:
    data = load_data()
    return data.get("gacha_claimed", {}).get(str(chat_id), {})

def claim_character(chat_id: int, user_id: int, char_id: str):
    data = load_data()
    claimed = data.setdefault("gacha_claimed", {}).setdefault(str(chat_id), {})
    claimed[char_id] = user_id
    save_data(data)

def unclaim_character(chat_id: int, char_id: str):
    data = load_data()
    claimed = data.get("gacha_claimed", {}).get(str(chat_id), {})
    if char_id in claimed:
        del claimed[char_id]
        save_data(data)

def get_roll_info(chat_id: int, user_id: int) -> dict:
    data = load_data()
    return data.get("gacha_rolls", {}).get(str(chat_id), {}).get(str(user_id), {"count": 0, "reset_at": ""})

def set_roll_info(chat_id: int, user_id: int, info: dict):
    data = load_data()
    rolls = data.setdefault("gacha_rolls", {}).setdefault(str(chat_id), {})
    rolls[str(user_id)] = info
    save_data(data)


# ── Bounties ───────────────────────────────────────────────
def get_bounties(chat_id: int) -> dict:
    data = load_data()
    return data.get("bounties", {}).get(str(chat_id), {})

def set_bounty(chat_id: int, target_uid: int, amount: int, placed_by: int):
    data = load_data()
    bounties = data.setdefault("bounties", {}).setdefault(str(chat_id), {})
    existing = bounties.get(str(target_uid), {}).get("amount", 0)
    bounties[str(target_uid)] = {"amount": existing + amount, "by": placed_by}
    save_data(data)

def remove_bounty(chat_id: int, target_uid: int) -> dict | None:
    data = load_data()
    bounties = data.get("bounties", {}).get(str(chat_id), {})
    if str(target_uid) in bounties:
        bounty = bounties.pop(str(target_uid))
        save_data(data)
        return bounty
    return None


# ── Clans ──────────────────────────────────────────────────
def get_all_clans(chat_id: int) -> dict:
    data = load_data()
    return data.get("clans", {}).get(str(chat_id), {})

def get_clan(chat_id: int, clan_name: str) -> dict | None:
    data = load_data()
    return data.get("clans", {}).get(str(chat_id), {}).get(clan_name)

def save_clan(chat_id: int, clan_name: str, clan_data: dict):
    data = load_data()
    clans = data.setdefault("clans", {}).setdefault(str(chat_id), {})
    clans[clan_name] = clan_data
    save_data(data)

def delete_clan(chat_id: int, clan_name: str):
    data = load_data()
    clans = data.get("clans", {}).get(str(chat_id), {})
    if clan_name in clans:
        del clans[clan_name]
        save_data(data)

def get_user_clan(chat_id: int, user_id: int) -> str | None:
    data = load_data()
    return data.get("user_clans", {}).get(str(chat_id), {}).get(str(user_id))

def set_user_clan(chat_id: int, user_id: int, clan_name: str | None):
    data = load_data()
    uc = data.setdefault("user_clans", {}).setdefault(str(chat_id), {})
    if clan_name is None:
        uc.pop(str(user_id), None)
    else:
        uc[str(user_id)] = clan_name
    save_data(data)
