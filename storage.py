# ==========================================
# KNTU Bot 25 — Persistent Data Store (JSON)
# ==========================================

import json
import os
import threading

_DEFAULT_DATA_FILE = os.path.join(os.path.dirname(__file__), "data.json")
DATA_FILE = os.environ.get("DATA_FILE", _DEFAULT_DATA_FILE)
_lock = threading.Lock()

_DEFAULT = {
    "group_lang": {},       # chat_id -> "fa" | "en"
    "lagabs": {},           # chat_id -> {user_id: nickname}
    "news_channels": {},    # chat_id -> [channel_username, ...]
    "debug": False,
    "seen_members": {},     # chat_id -> [user_id, ...]
    "user_names": {},       # chat_id -> {user_id: display_name}
}


def _load() -> dict:
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return dict(_DEFAULT)


def _save(data: dict):
    parent_dir = os.path.dirname(DATA_FILE)
    if parent_dir:
        os.makedirs(parent_dir, exist_ok=True)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_data() -> dict:
    with _lock:
        return _load()


def save_data(data: dict):
    with _lock:
        _save(data)


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
    """Track a member; return True if they are new (first time seen)."""
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
    """Add a warn to a user; return their new total warns."""
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
    """Return the date string of last daily claim, or empty string."""
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


# ---- Jail (Savak) ----

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
    """Returns {company: shares} for a user."""
    data = load_data()
    return data.get("stocks", {}).get(str(chat_id), {}).get(str(user_id), {})


def set_stocks(chat_id: int, user_id: int, stocks: dict):
    data = load_data()
    s = data.setdefault("stocks", {}).setdefault(str(chat_id), {})
    s[str(user_id)] = stocks
    save_data(data)


# ---- Daily Events ----

def get_daily_event(chat_id: int) -> dict:
    """Returns {"date": "YYYY-MM-DD", "event": "...", "effect": ...} or {}."""
    data = load_data()
    return data.get("daily_events", {}).get(str(chat_id), {})


def set_daily_event(chat_id: int, event_data: dict):
    data = load_data()
    events = data.setdefault("daily_events", {})
    events[str(chat_id)] = event_data
    save_data(data)
