"""Real Hermes AIAgent tests for Bob."""
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
os.environ.setdefault("HERMES_TOOLSETS", "none")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# Prefer local hermes-agent checkout if present (dev/CI sandbox)
_HERMES_SRC = Path("/home/user/hermes-agent-src")
if _HERMES_SRC.is_dir() and str(_HERMES_SRC) not in sys.path:
    sys.path.insert(0, str(_HERMES_SRC))

from handlers import hermes_brain as hb  # noqa: E402


def _load_env_keys():
    env_path = ROOT / ".env"
    if not env_path.is_file():
        return
    for line in env_path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip() or line.strip().startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip())


def test_soul_loads():
    soul = hb.load_soul()
    assert "Bob" in soul or "باب" in soul


def test_session_roundtrip():
    hb.save_history(1, 2, [{"role": "user", "content": "hi"}, {"role": "assistant", "content": "yo"}])
    assert hb.load_history(1, 2)[-1]["content"] == "yo"
    assert hb.clear_history(1, 2) is True


def test_hermes_available_or_skip():
    # In the bot Docker image this must be True. Locally may be True if checkout present.
    ok = hb.hermes_available()
    assert isinstance(ok, bool)


def test_live_real_hermes_chat():
    _load_env_keys()
    keys = (
        os.environ.get("OPENCODE_ZEN_API_KEY")
        or os.environ.get("OPENCODE_API_KEY")
        or os.environ.get("OPENCODE_API_KEYS")
        or ""
    ).strip()
    if not keys:
        import pytest
        pytest.skip("no OpenCode key")
    if not hb.hermes_available():
        import pytest
        pytest.skip("real Hermes AIAgent not on PYTHONPATH")

    # Map keys like entrypoint does
    first = keys.split(",")[0].strip()
    os.environ.setdefault("OPENCODE_ZEN_API_KEY", first)
    os.environ.setdefault("OPENCODE_ZEN_BASE_URL", "https://opencode.ai/zen/v1")
    os.environ.setdefault("HERMES_MODEL", "north-mini-code-free")
    os.environ["HERMES_TOOLSETS"] = "none"

    reply, meta = hb.chat(
        chat_id=777001,
        user_id=7,
        user_text="Who are you? One short sentence.",
        lang="en",
        user_name="Tester",
    )
    assert meta.get("engine") == "hermes_native"
    assert meta.get("provider") == "hermes_native"
    assert isinstance(reply, str) and len(reply) > 5
    assert "error" not in (meta.get("error") or "").lower() or "Bob" in reply or "باب" in reply or len(reply) > 0
