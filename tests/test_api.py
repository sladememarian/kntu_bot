"""Casino API tests — real aiohttp app + real wallet storage."""
from __future__ import annotations

import json
import urllib.error
import urllib.request

import pytest


def _get(url: str):
    with urllib.request.urlopen(url, timeout=5) as r:
        return json.loads(r.read().decode())


def _post(url: str, payload: dict):
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"}, method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        try:
            return e.code, json.loads(body)
        except Exception:
            return e.code, {"error": body}


def test_balance_get_and_post(server_base_url, seed_wallet):
    chat_id, user_id = 1, 2
    seed_wallet(chat_id, user_id, 500)
    d = _get(f"{server_base_url}/api/balance?chat_id={chat_id}&user_id={user_id}")
    assert d["balance"] == 500
    code, d2 = _post(f"{server_base_url}/api/balance", {
        "chat_id": chat_id, "user_id": user_id, "delta": -120
    })
    assert code == 200
    assert d2["balance"] == 380
    assert d2["applied_delta"] == -120


def test_delta_clamp_accounting(server_base_url, seed_wallet, monkeypatch):
    """balance 50, lose 80 → applied loss 50, balance 0."""
    chat_id, user_id = 11, 22
    seed_wallet(chat_id, user_id, 50)
    calls = []

    def fake_loss(cid, amt):
        calls.append((cid, amt))

    monkeypatch.setattr(
        "handlers.casino._process_casino_loss", fake_loss, raising=False
    )
    # ensure import path used inside handler works
    import handlers.casino as casino_mod
    monkeypatch.setattr(casino_mod, "_process_casino_loss", fake_loss)

    code, d = _post(f"{server_base_url}/api/balance", {
        "chat_id": chat_id, "user_id": user_id, "delta": -80
    })
    assert code == 200
    assert d["balance"] == 0
    assert d["applied_delta"] == -50
    assert d["requested_delta"] == -80


def test_delta_out_of_range(server_base_url, seed_wallet):
    seed_wallet(3, 4, 100)
    code, d = _post(f"{server_base_url}/api/balance", {
        "chat_id": 3, "user_id": 4, "delta": 5_000_000
    })
    assert code == 400
    assert "range" in d.get("error", "")


def test_insufficient_on_zero(server_base_url, seed_wallet):
    seed_wallet(5, 6, 0)
    code, d = _post(f"{server_base_url}/api/balance", {
        "chat_id": 5, "user_id": 6, "delta": -10
    })
    assert code == 400
    assert d["balance"] == 0


def test_poker_join_start_fold_winner(server_base_url, seed_wallet):
    chat_id = 777
    players = [(101, "A"), (102, "B"), (103, "C"), (104, "D")]
    for uid, _ in players:
        seed_wallet(chat_id, uid, 500)

    for uid, name in players:
        code, d = _post(f"{server_base_url}/api/poker/join", {
            "chat_id": chat_id, "user_id": uid, "name": name, "bet": 50
        })
        assert code == 200, d
        assert d["count"] >= 1

    st = _get(f"{server_base_url}/api/poker/status?chat_id={chat_id}&user_id=101")
    assert st["count"] == 4
    assert st["state"] == "waiting"

    code, started = _post(f"{server_base_url}/api/poker/start", {"chat_id": chat_id})
    assert code == 200, started
    assert started["state"] == "preflop"
    assert started.get("turn_user_id") is not None
    assert started["pot"] == 200

    # Fold three players until one remains
    # Always fold current turn_user_id until finished
    guard = 0
    winner = None
    while guard < 20:
        guard += 1
        st = _get(f"{server_base_url}/api/poker/status?chat_id={chat_id}&user_id=101")
        if st.get("state") == "finished":
            winner = st.get("winner")
            break
        turn = st.get("turn_user_id")
        assert turn, st
        code, d = _post(f"{server_base_url}/api/poker/action", {
            "chat_id": chat_id, "user_id": turn, "action": "fold"
        })
        assert code == 200, d
        if d.get("status") == "game_over":
            winner = d.get("winner")
            assert d.get("all_hands") is not None
            break

    assert winner is not None
    assert "name" in winner
    # final status carries winner
    st = _get(f"{server_base_url}/api/poker/status?chat_id={chat_id}&user_id=101")
    assert st["state"] == "finished"
    assert st.get("winner")
    assert st.get("turn_user_id") is None


def test_poker_not_your_turn(server_base_url, seed_wallet):
    chat_id = 888
    players = [(201, "A"), (202, "B"), (203, "C"), (204, "D")]
    for uid, name in players:
        seed_wallet(chat_id, uid, 300)
        _post(f"{server_base_url}/api/poker/join", {
            "chat_id": chat_id, "user_id": uid, "name": name, "bet": 25
        })
    _post(f"{server_base_url}/api/poker/start", {"chat_id": chat_id})
    st = _get(f"{server_base_url}/api/poker/status?chat_id={chat_id}&user_id=201")
    turn = st["turn_user_id"]
    other = next(uid for uid, _ in players if str(uid) != str(turn))
    code, d = _post(f"{server_base_url}/api/poker/action", {
        "chat_id": chat_id, "user_id": other, "action": "check"
    })
    assert code == 400
    assert "turn" in d.get("error", "")
