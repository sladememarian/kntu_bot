# ==========================================
# Bob's brain = REAL NousResearch Hermes Agent
# ==========================================
# Docs:
#   https://hermes-agent.nousresearch.com/docs/guides/python-library
#   https://hermes-agent.nousresearch.com/docs/user-guide/configuration
#
# Requires Hermes checkout on PYTHONPATH (see Dockerfile -> /opt/hermes-agent)
#   from run_agent import AIAgent
#
# Provider wiring (entrypoint maps bot env -> Hermes env):
#   OPENCODE_API_KEYS / OPENCODE_API_KEY  ->  OPENCODE_ZEN_API_KEY
#   OPENCODE_BASE_URL                    ->  OPENCODE_ZEN_BASE_URL
#   NVIDIA_API_KEY + NVIDIA_BASE_URL     ->  optional OpenAI-compat
#   GEMINI_API_KEY                       ->  GOOGLE_API_KEY
#
# Phase 2 improvements:
#   - Persistent memory enabled (skip_memory=False)
#   - Session IDs per chat+user for context continuity
#   - Soul identity loaded properly (load_soul_identity=True)
#   - Tool-enabled: memory, session_search, skills, web, kanban, cronjob, todo
#   - Model fallback chain: nvidia -> gemini -> opencode_zen -> north-mini
#   - Agent pool: reuse AIAgent per session instead of fresh per call
# ==========================================

from __future__ import annotations

import hashlib
import json
import logging
import os
import threading
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger("kntu_bot25.hermes_brain")

_ROOT = Path(__file__).resolve().parents[1]
_SOUL_PATH = Path(os.environ.get("BOB_SOUL_PATH") or (_ROOT / "hermes" / "SOUL.md"))
_SESSIONS_DIR = Path(os.environ.get("BOB_SESSIONS_DIR") or (_ROOT / "data" / "bob_sessions"))
_SESSIONS_DIR.mkdir(parents=True, exist_ok=True)

_lock = threading.Lock()
_stats = {
    "calls": 0,
    "errors": 0,
    "provider_last": "",
    "model_last": "",
    "engine": "hermes_native",
    "born": time.time(),
    "sessions": 0,
    "hermes_import_ok": False,
}


def _env(name: str, default: str = "") -> str:
    return (os.environ.get(name) or default).strip()


def _split(raw: str) -> list[str]:
    if not raw:
        return []
    return [p.strip() for p in raw.replace("\n", ",").split(",") if p.strip()]


def load_soul() -> str:
    try:
        if _SOUL_PATH.is_file():
            return _SOUL_PATH.read_text(encoding="utf-8").strip()
    except Exception as e:
        logger.warning("SOUL.md read failed: %s", e)
    return (
        "You are Bob (), son of Markov and Ophelia, the group AI of KNTU Bot 25. "
        "Be helpful, witty, bilingual (Persian + English). Users call you Bob."
    )


# ---------------------------------------------------------------------------
# Session path helpers (legacy JSON-based, kept for /bob reset + stats)
# ---------------------------------------------------------------------------

def _session_path(chat_id: int, user_id: int) -> Path:
    return _SESSIONS_DIR / f"{chat_id}_{user_id}.json"


def load_history(chat_id: int, user_id: int, limit: int = 30) -> list[dict]:
    path = _session_path(chat_id, user_id)
    if not path.is_file():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return (data.get("messages") or [])[-limit:]
    except Exception:
        return []


def save_history(chat_id: int, user_id: int, messages: list[dict], max_keep: int = 50):
    path = _session_path(chat_id, user_id)
    payload = {"messages": messages[-max_keep:], "updated": time.time()}
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)


def clear_history(chat_id: int, user_id: int) -> bool:
    path = _session_path(chat_id, user_id)
    if path.is_file():
        path.unlink(missing_ok=True)
        return True
    return False


def session_count() -> int:
    try:
        return len(list(_SESSIONS_DIR.glob("*.json")))
    except Exception:
        return 0


def hermes_available() -> bool:
    try:
        from run_agent import AIAgent  # noqa: F401
        return True
    except Exception as e:
        logger.info("Hermes AIAgent not importable: %s", e)
        return False


# ---------------------------------------------------------------------------
# Provider resolution (multi-provider with fallback chain)
# ---------------------------------------------------------------------------

def _resolve_primary_provider() -> tuple[str, str]:
    """Pick the PRIMARY api_key + base_url for AIAgent.

    Priority order (user-configured):
      1. NVIDIA (z-ai/glm-5.2, thinkingmachines/inkling, deepseek-v4-flash)
      2. GOOGLE/GEMINI (gemini-3.1-flash-lite, gemini-3)
      3. OpenCode Zen (big-pickle, north-mini-code-free)
    """
    # 1. NVIDIA
    nvidia_key = _env("NVIDIA_API_KEY")
    if nvidia_key:
        return nvidia_key, _env("NVIDIA_BASE_URL") or "https://integrate.api.nvidia.com/v1"

    # 2. Gemini
    gemini_key = _env("GEMINI_API_KEY") or _env("GOOGLE_API_KEY")
    if gemini_key:
        return gemini_key, "https://generativelanguage.googleapis.com/v1beta/openai"

    # 3. OpenCode Zen
    zen_key = (
        _env("OPENCODE_ZEN_API_KEY")
        or _env("OPENCODE_API_KEY")
        or (_split(_env("OPENCODE_API_KEYS")) or [""])[0]
    )
    if zen_key:
        base = (
            _env("OPENCODE_ZEN_BASE_URL")
            or _env("OPENCODE_BASE_URL")
            or "https://opencode.ai/zen/v1"
        )
        return zen_key, base

    return "", ""


def _resolve_fallback_model() -> dict[str, Any] | None:
    """Build a fallback_model dict for AIAgent.

    When the primary model/provider fails, Hermes tries these in order.
    """
    fallbacks = []

    # Check if NVIDIA is primary - if so, add Gemini + OpenCode as fallbacks
    nvidia_key = _env("NVIDIA_API_KEY")
    gemini_key = _env("GEMINI_API_KEY") or _env("GOOGLE_API_KEY")
    zen_key = _env("OPENCODE_ZEN_API_KEY") or _env("OPENCODE_API_KEY") or (_split(_env("OPENCODE_API_KEYS")) or [""])[0]

    if nvidia_key:
        # Primary is NVIDIA - add Gemini and OpenCode as fallbacks
        if gemini_key:
            fallbacks.append({
                "model": _env("FALLBACK_MODEL_1") or "gemini-2.0-flash",
                "api_key": gemini_key,
                "base_url": "https://generativelanguage.googleapis.com/v1beta/openai",
            })
        if zen_key:
            fallbacks.append({
                "model": _env("FALLBACK_MODEL_2") or "big-pickle",
                "api_key": zen_key,
                "base_url": _env("OPENCODE_BASE_URL") or "https://opencode.ai/zen/v1",
            })
    elif gemini_key:
        # Primary is Gemini - add NVIDIA and OpenCode as fallbacks
        if nvidia_key:
            fallbacks.append({
                "model": _env("FALLBACK_MODEL_1") or "deepseek-ai/deepseek-v4-flash",
                "api_key": nvidia_key,
                "base_url": _env("NVIDIA_BASE_URL") or "https://integrate.api.nvidia.com/v1",
            })
        if zen_key:
            fallbacks.append({
                "model": _env("FALLBACK_MODEL_2") or "big-pickle",
                "api_key": zen_key,
                "base_url": _env("OPENCODE_BASE_URL") or "https://opencode.ai/zen/v1",
            })
    else:
        # Primary is OpenCode - add Gemini as fallback
        if gemini_key:
            fallbacks.append({
                "model": _env("FALLBACK_MODEL_1") or "gemini-2.0-flash",
                "api_key": gemini_key,
                "base_url": "https://generativelanguage.googleapis.com/v1beta/openai",
            })

    if not fallbacks:
        return None
    return fallbacks[0] if len(fallbacks) == 1 else fallbacks


def _resolve_model() -> str:
    """Resolve the primary model name."""
    # Explicit HERMES_MODEL takes precedence
    m = _env("HERMES_MODEL")
    if m:
        return _split(m)[0]

    # Otherwise derive from provider
    nvidia_key = _env("NVIDIA_API_KEY")
    if nvidia_key:
        models = _split(_env("NVIDIA_MODELS"))
        return models[0] if models else "z-ai/glm-5.2"

    gemini_key = _env("GEMINI_API_KEY") or _env("GOOGLE_API_KEY")
    if gemini_key:
        return _env("GEMINI_MODEL") or "gemini-2.0-flash"

    m = _env("OPENCODE_MODELS")
    if m:
        return _split(m)[0]

    return "north-mini-code-free"


# ---------------------------------------------------------------------------
# Toolsets — what Hermes is allowed to use
# ---------------------------------------------------------------------------

def _toolsets() -> list[str] | None:
    """Resolve enabled toolsets.

    Safe tools for Telegram group chat:
      memory, session_search, skill_manage, skill_view, skills_list,
      web_search, web_extract, todo, kanban, cronjob

    Dangerous tools kept disabled:
      terminal, execute_code, write_file, patch, process
    """
    raw = _env("HERMES_TOOLSETS")
    if raw:
        if raw.lower() in ("none", "off", "false", "0"):
            return []
        return _split(raw)

    # Default: safe tools for Telegram group chat
    return [
        "memory",
        "session_search",
        "skill_manage",
        "skill_view",
        "skills_list",
        "web_search",
        "web_extract",
        "todo",
        "kanban",
        "cronjob",
        "clarify",
        "delegate_task",
        "text_to_speech",
        "tool_search",
        "tool_describe",
        "tool_call",
    ]


# ---------------------------------------------------------------------------
# Agent pool — reuse AIAgent per session instead of fresh per call
# ---------------------------------------------------------------------------

_agent_pool: dict[str, Any] = {}
_agent_pool_lock = threading.Lock()


def _make_agent(system: str, session_key: str = ""):
    """Construct or reuse an AIAgent for the given session.

    Agents are cached by session_key so Hermes preserves in-memory context
    (tool state, conversation context) across calls within the same session.
    """
    from run_agent import AIAgent

    api_key, base_url = _resolve_primary_provider()
    model = _resolve_model()
    toolsets = _toolsets()

    # Check if we can reuse a cached agent
    if session_key and session_key in _agent_pool:
        cached = _agent_pool[session_key]
        # Update the system prompt for this turn
        cached.ephemeral_system_prompt = system
        return cached, model, base_url

    kwargs: dict[str, Any] = {
        "model": model,
        "quiet_mode": True,
        "skip_context_files": True,
        "skip_memory": False,  # Phase 2: ENABLE persistent memory
        "max_iterations": int(_env("HERMES_MAX_ITERATIONS") or "20"),
        "platform": "telegram",
        "load_soul_identity": True,  # Phase 2: proper soul integration
        "session_id": session_key or None,
    }

    if api_key:
        kwargs["api_key"] = api_key
    if base_url:
        kwargs["base_url"] = base_url
    if toolsets is not None:
        kwargs["enabled_toolsets"] = toolsets

    # Ephemeral system prompt (language + user context)
    kwargs["ephemeral_system_prompt"] = system

    # Model fallback
    fallback = _resolve_fallback_model()
    if fallback:
        kwargs["fallback_model"] = fallback

    agent = AIAgent(**kwargs)

    # Cache in pool (limit pool size to prevent memory leaks)
    if session_key:
        with _agent_pool_lock:
            if len(_agent_pool) > 100:
                # Evict oldest entries
                oldest = sorted(_agent_pool.keys())[:50]
                for k in oldest:
                    _agent_pool.pop(k, None)
            _agent_pool[session_key] = agent

    return agent, model, base_url


# ---------------------------------------------------------------------------
# Main chat function
# ---------------------------------------------------------------------------

def chat(
    *,
    chat_id: int,
    user_id: int,
    user_text: str,
    lang: str = "fa",
    user_name: str = "",
) -> tuple[str, dict[str, Any]]:
    """
    One turn through REAL Hermes AIAgent.
    Returns (reply_text, meta).
    """
    system = load_soul()
    if lang == "fa":
        system += (
            "\n\nLanguage: Prefer Persian (Farsi) when the user writes Persian; "
            "match the user's language. Keep replies Telegram-friendly."
        )
    else:
        system += "\n\nLanguage: Prefer English unless the user writes another language."
    if user_name:
        system += f"\n\nYou are talking to: {user_name}."

    # Stable session key for agent reuse + Hermes session_id
    session_key = f"bob_{chat_id}_{user_id}"

    history = load_history(chat_id, user_id)
    meta: dict[str, Any] = {
        "provider": "hermes_native",
        "model": _resolve_model(),
        "engine": "hermes_native",
        "error": "",
    }

    if not hermes_available():
        meta["error"] = "run_agent.AIAgent not importable -- Hermes not installed in image"
        with _lock:
            _stats["calls"] += 1
            _stats["errors"] += 1
            _stats["hermes_import_ok"] = False
        if lang == "fa":
            return "  مغز هرمس نصب نیست -- ادمین باید ایمیج رو rebuild کنه.", meta
        return "Hermes agent not installed -- rebuild the Docker image.", meta

    try:
        agent, model, base = _make_agent(system, session_key)
        meta["model"] = model
        meta["base_url"] = base

        # Multi-turn: pass prior messages as conversation_history
        result = agent.run_conversation(
            user_message=user_text,
            conversation_history=list(history) if history else None,
            system_message=system,
        )
        if isinstance(result, dict):
            reply = (result.get("final_response") or "").strip()
            # Prefer Hermes' returned message list for next turn if present
            msgs = result.get("messages")
            if isinstance(msgs, list) and msgs:
                cleaned = []
                for m in msgs:
                    if not isinstance(m, dict):
                        continue
                    role = m.get("role")
                    content = m.get("content")
                    if role in ("user", "assistant") and isinstance(content, str) and content.strip():
                        cleaned.append({"role": role, "content": content.strip()})
                if cleaned:
                    history = cleaned
        else:
            reply = str(result or "").strip()

        if not reply:
            raise RuntimeError("Hermes returned empty response")

        # If Hermes didn't give us a clean history, append manually
        if not history or history[-1].get("content") != reply:
            history = list(load_history(chat_id, user_id))
            history.append({"role": "user", "content": user_text})
            history.append({"role": "assistant", "content": reply})
        save_history(chat_id, user_id, history)

        with _lock:
            _stats["calls"] += 1
            _stats["provider_last"] = "hermes_native"
            _stats["model_last"] = model
            _stats["hermes_import_ok"] = True
            _stats["sessions"] = session_count()

        return reply, meta

    except Exception as e:
        logger.exception("Hermes AIAgent failed")
        meta["error"] = str(e)[:300]
        with _lock:
            _stats["calls"] += 1
            _stats["errors"] += 1
            _stats["hermes_import_ok"] = hermes_available()
        if lang == "fa":
            return f"خطای مغز هرمس : {e}", meta
        return f"Hermes brain error: {e}", meta


# ---------------------------------------------------------------------------
# Stats and diagnostics
# ---------------------------------------------------------------------------

def get_stats() -> dict[str, Any]:
    with _lock:
        s = dict(_stats)
    s["sessions"] = session_count()
    s["soul_path"] = str(_SOUL_PATH)
    s["soul_loaded"] = _SOUL_PATH.is_file()
    s["hermes_home"] = _env("HERMES_HOME")
    s["hermes_agent_dir"] = _env("HERMES_AGENT_DIR") or "/opt/hermes-agent"
    s["hermes_import_ok"] = hermes_available()
    s["model"] = _resolve_model()
    s["fallback_model"] = _env("FALLBACK_MODEL_1") or "gemini-2.0-flash"
    key, base = _resolve_primary_provider()
    s["api_key_set"] = bool(key)
    s["base_url"] = base
    s["toolsets"] = _toolsets()
    s["memory_enabled"] = True  # Phase 2: always enabled
    s["agent_pool_size"] = len(_agent_pool)
    s["age_days"] = max(0.0, (time.time() - s.get("born", time.time())) / 86400.0)
    # provider presence (for /bobstats display)
    s["providers"] = []
    if _env("NVIDIA_API_KEY"):
        s["providers"].append({
            "name": "nvidia",
            "models": _split(_env("NVIDIA_MODELS") or "z-ai/glm-5.2"),
            "keys": 1,
            "base": _env("NVIDIA_BASE_URL") or "https://integrate.api.nvidia.com/v1",
        })
    if _env("GEMINI_API_KEY") or _env("GOOGLE_API_KEY"):
        s["providers"].append({
            "name": "gemini",
            "models": [_env("GEMINI_MODEL") or "gemini-2.0-flash"],
            "keys": 1,
            "base": "google",
        })
    if _env("OPENCODE_ZEN_API_KEY") or _env("OPENCODE_API_KEY") or _env("OPENCODE_API_KEYS"):
        s["providers"].append({
            "name": "opencode_zen",
            "models": _split(_env("OPENCODE_MODELS") or "big-pickle,north-mini-code-free"),
            "keys": len(_split(_env("OPENCODE_API_KEYS") or _env("OPENCODE_API_KEY") or _env("OPENCODE_ZEN_API_KEY"))),
            "base": _env("OPENCODE_ZEN_BASE_URL") or _env("OPENCODE_BASE_URL") or "https://opencode.ai/zen/v1",
        })
    return s


def ping_providers() -> list[dict[str, Any]]:
    """Live ping via real Hermes AIAgent (one short chat)."""
    results = []
    ok = hermes_available()
    entry = {
        "provider": "hermes_native",
        "model": _resolve_model(),
        "ok": False,
        "error": "",
        "sample": "",
    }
    if not ok:
        entry["error"] = "AIAgent import failed"
        return [entry]
    try:
        reply, meta = chat(
            chat_id=0,
            user_id=0,
            user_text="Reply with exactly: pong",
            lang="en",
            user_name="ping",
        )
        entry["ok"] = bool(reply) and not meta.get("error")
        entry["sample"] = (reply or "")[:80]
        entry["error"] = meta.get("error") or ""
        entry["model"] = meta.get("model") or entry["model"]
    except Exception as e:
        entry["error"] = str(e)[:200]
    results.append(entry)
    return results
