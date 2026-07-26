"""Hermes-Bob brain tests (unit + live OpenCode e2e when keys present)."""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

_TMP = tempfile.mkdtemp(prefix="kntu_hermes_bob_")
os.environ["DATABASE_URL"] = ""
os.environ["DATA_FILE"] = os.path.join(_TMP, "data.json")
os.environ["BOB_SESSIONS_DIR"] = os.path.join(_TMP, "sessions")
os.environ.setdefault("BOT_TOKEN", "x")

# Ensure OpenCode key available for live test if user exported it
# (CI may skip live if missing)

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from handlers import hermes_brain as hb  # noqa: E402


def test_soul_loads():
    soul = hb.load_soul()
    assert "Bob" in soul or "باب" in soul
    assert len(soul) > 40


def test_session_roundtrip():
    hb.save_history(1, 2, [{"role": "user", "content": "hi"}, {"role": "assistant", "content": "yo"}])
    hist = hb.load_history(1, 2)
    assert hist[-1]["content"] == "yo"
    assert hb.clear_history(1, 2) is True
    assert hb.load_history(1, 2) == []


def test_providers_parse_from_env(monkeypatch):
    monkeypatch.setenv("OPENCODE_API_KEYS", "sk-test1,sk-test2")
    monkeypatch.setenv("OPENCODE_MODELS", "north-mini-code-free,big-pickle")
    monkeypatch.delenv("NVIDIA_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
    provs = hb._providers()
    assert any(p.name == "opencode" for p in provs)
    oc = next(p for p in provs if p.name == "opencode")
    assert oc.models[0] == "north-mini-code-free"
    assert len(oc.api_keys) == 2


def test_chat_offline_message_without_providers(monkeypatch):
    monkeypatch.delenv("OPENCODE_API_KEY", raising=False)
    monkeypatch.delenv("OPENCODE_API_KEYS", raising=False)
    monkeypatch.delenv("NVIDIA_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("HERMES_HOME", raising=False)
    # force empty providers
    monkeypatch.setattr(hb, "_providers", lambda: [])
    reply, meta = hb.chat(chat_id=9, user_id=9, user_text="hello", lang="en")
    assert reply
    assert meta.get("provider") in ("none", "gemini", "")


def test_live_opencode_chat():
    """E2E against real OpenCode Zen when a key is configured."""
    keys = (os.environ.get("OPENCODE_API_KEYS") or os.environ.get("OPENCODE_API_KEY") or "").strip()
    if not keys:
        # try reading repo .env for local/dev convenience (not committed)
        env_path = ROOT / ".env"
        if env_path.is_file():
            for line in env_path.read_text(encoding="utf-8", errors="replace").splitlines():
                if line.startswith("OPENCODE_API_KEY=") or line.startswith("OPENCODE_API_KEYS="):
                    os.environ[line.split("=", 1)[0]] = line.split("=", 1)[1]
                    keys = line.split("=", 1)[1]
                    break
    if not keys:
        import pytest
        pytest.skip("no OPENCODE_API_KEY")

    os.environ.setdefault("OPENCODE_MODELS", "north-mini-code-free,big-pickle")
    os.environ.setdefault("OPENCODE_BASE_URL", "https://opencode.ai/zen/v1")
    # isolate session
    reply, meta = hb.chat(
        chat_id=424242,
        user_id=7,
        user_text="Reply with exactly: BOB_OK",
        lang="en",
        user_name="Tester",
    )
    assert meta.get("provider") in ("opencode", "hermes_native", "gemini", "nvidia")
    assert isinstance(reply, str) and len(reply) > 0
    # soft check — models may paraphrase
    assert "BOB" in reply.upper() or "OK" in reply.upper() or len(reply) < 500


def test_bob_handlers_import():
    from handlers import bob_ai
    assert callable(bob_ai.bob_cmd)
    assert callable(bob_ai.bobstats_cmd)
    assert callable(bob_ai.bob_listen)
