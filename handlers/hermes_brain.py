# ==========================================
# Bob's brain = REAL NousResearch Hermes Agent
# ==========================================
# Phase 3 fixes:
#   - Unified provider/model resolution (model name → correct provider)
#   - Smart model health tracking (10 failures → 1.5d cooldown, 2d → retry)
#   - Prefer last-working model (don't restart from scratch)
#   - OpenCode Zen primary (NVIDIA blocked from EU sandbox)
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
_HEALTH_PATH = Path(os.environ.get("BOB_DATA_DIR") or (_ROOT / "data")) / "model_health.json"
_SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
_HEALTH_PATH.parent.mkdir(parents=True, exist_ok=True)

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
# Session path helpers
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
# Model Health Tracking
# ---------------------------------------------------------------------------
# Tracks consecutive failures per model. After 10 failures, model is
# cooldown-blocked for 1.5 days. After 2 days, cooldown expires and
# model is retried. Last-working model is preferred on next call.

_COOLDOWN_SECONDS = int(os.environ.get("MODEL_COOLDOWN_SECONDS") or str(int(1.5 * 86400)))  # 1.5 days
_MAX_FAILURES = int(os.environ.get("MODEL_MAX_FAILURES") or "10")
_RETRY_AFTER_SECONDS = int(os.environ.get("MODEL_RETRY_AFTER") or str(2 * 86400))  # 2 days

_health_lock = threading.Lock()


def _load_health() -> dict[str, Any]:
    """Load model health state from disk."""
    try:
        if _HEALTH_PATH.is_file():
            return json.loads(_HEALTH_PATH.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}


def _save_health(data: dict[str, Any]):
    """Persist model health state to disk."""
    try:
        tmp = _HEALTH_PATH.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(_HEALTH_PATH)
    except Exception as e:
        logger.warning("model health save failed: %s", e)


def _record_success(model: str):
    """Record a successful call for a model."""
    with _health_lock:
        h = _load_health()
        entry = h.get(model, {})
        entry["failures"] = 0
        entry["cooldown_until"] = 0
        entry["last_success"] = time.time()
        h["_last_working"] = model
        h[model] = entry
        _save_health(h)


def _record_failure(model: str):
    """Record a failed call. If consecutive failures >= _MAX_FAILURES, cooldown."""
    with _health_lock:
        h = _load_health()
        entry = h.get(model, {})
        entry["failures"] = entry.get("failures", 0) + 1
        entry["last_failure"] = time.time()
        if entry["failures"] >= _MAX_FAILURES:
            entry["cooldown_until"] = time.time() + _COOLDOWN_SECONDS
            logger.warning(
                "Model %s hit %d failures → cooldown for %.1f days",
                model, entry["failures"], _COOLDOWN_SECONDS / 86400,
            )
        h[model] = entry
        _save_health(h)


def _is_model_healthy(model: str) -> bool:
    """Check if a model is available (not in cooldown)."""
    with _health_lock:
        h = _load_health()
        entry = h.get(model, {})
        cooldown_until = entry.get("cooldown_until", 0)
        if cooldown_until > 0:
            now = time.time()
            if now < cooldown_until:
                # Still in cooldown. But after 2x cooldown period, allow retry.
                failed_at = entry.get("last_failure", cooldown_until - _COOLDOWN_SECONDS)
                if now - failed_at > _RETRY_AFTER_SECONDS:
                    logger.info("Model %s cooldown expired (2d passed) → retrying", model)
                    return True
                return False
        return True


def _get_health_report() -> dict[str, Any]:
    """Get current health state for display."""
    with _health_lock:
        return _load_health()


# ---------------------------------------------------------------------------
# Provider/Model Resolution (UNIFIED)
# ---------------------------------------------------------------------------
# Each model is matched to its correct provider. No more sending OpenCode
# model names to NVIDIA endpoint.
#
# Chain order (configurable via env):
#   1. OpenCode Zen (big-pickle, north-mini-code-free)
#   2. Gemini (gemini-2.0-flash)
#   3. NVIDIA (z-ai/glm-5.2, etc.) — blocked from EU sandbox but kept for completeness

def _build_model_chain() -> list[dict[str, Any]]:
    """Build the full model chain: list of {model, api_key, base_url, provider}.

    Models are tried in order. Health tracking skips cooldown models.
    The last-working model is moved to the front.
    """
    chain = []

    # --- OpenCode Zen (primary - works from EU sandbox) ---
    zen_keys = _split(_env("OPENCODE_API_KEYS"))
    zen_key_single = _env("OPENCODE_ZEN_API_KEY") or _env("OPENCODE_API_KEY")
    if zen_key_single and zen_key_single not in zen_keys:
        zen_keys.insert(0, zen_key_single)
    zen_base = _env("OPENCODE_ZEN_BASE_URL") or _env("OPENCODE_BASE_URL") or "https://opencode.ai/zen/v1"
    opencode_models = _split(_env("OPENCODE_MODELS") or "big-pickle,north-mini-code-free")
    for model in opencode_models:
        for key in zen_keys:
            chain.append({
                "model": model,
                "api_key": key,
                "base_url": zen_base,
                "provider": "opencode_zen",
            })
            break  # one key per model (rotate keys via health tracking if needed)

    # --- Gemini (fallback) ---
    gemini_key = _env("GEMINI_API_KEY") or _env("GOOGLE_API_KEY")
    if gemini_key:
        gemini_models = _split(_env("GEMINI_MODELS") or _env("GEMINI_MODEL") or "gemini-2.0-flash")
        for model in gemini_models:
            chain.append({
                "model": model,
                "api_key": gemini_key,
                "base_url": "https://generativelanguage.googleapis.com/v1beta/openai",
                "provider": "gemini",
            })

    # --- NVIDIA (last resort - may be blocked from EU) ---
    nvidia_key = _env("NVIDIA_API_KEY")
    if nvidia_key:
        nvidia_models = _split(_env("NVIDIA_MODELS") or "z-ai/glm-5.2")
        for model in nvidia_models:
            chain.append({
                "model": model,
                "api_key": nvidia_key,
                "base_url": _env("NVIDIA_BASE_URL") or "https://integrate.api.nvidia.com/v1",
                "provider": "nvidia",
            })

    return chain


def _resolve_best_model() -> tuple[str, str, str, str]:
    """Pick the best available model based on health tracking.

    Returns (model, api_key, base_url, provider).
    """
    chain = _build_model_chain()
    if not chain:
        return ("north-mini-code-free", "", "https://opencode.ai/zen/v1", "opencode_zen")

    # Check if last-working model is still healthy and in chain
    health = _get_health_report()
    last_working = health.get("_last_working", "")
    if last_working:
        for entry in chain:
            if entry["model"] == last_working and _is_model_healthy(last_working):
                logger.info("Using last-working model: %s", last_working)
                return (entry["model"], entry["api_key"], entry["base_url"], entry["provider"])

    # First healthy model in chain
    for entry in chain:
        if _is_model_healthy(entry["model"]):
            return (entry["model"], entry["api_key"], entry["base_url"], entry["provider"])

    # All models in cooldown — use the one with shortest remaining cooldown
    best = chain[0]
    best_until = health.get(best["model"], {}).get("cooldown_until", 0)
    for entry in chain[1:]:
        until = health.get(entry["model"], {}).get("cooldown_until", 0)
        if until < best_until or best_until <= 0:
            best = entry
            best_until = until
    logger.warning("All models in cooldown, using: %s", best["model"])
    return (best["model"], best["api_key"], best["base_url"], best["provider"])


def _resolve_fallback_model() -> dict[str, Any] | None:
    """Build fallback_model dict for AIAgent.

    Returns the NEXT healthy model in chain after the primary.
    """
    chain = _build_model_chain()
    model, _, _, _ = _resolve_best_model()

    # Find primary in chain, return next healthy one
    found_primary = False
    for entry in chain:
        if entry["model"] == model and not found_primary:
            found_primary = True
            continue
        if found_primary and _is_model_healthy(entry["model"]):
            return {
                "model": entry["model"],
                "api_key": entry["api_key"],
                "base_url": entry["base_url"],
            }
    return None


# Legacy wrappers for stats display
def _resolve_primary_provider() -> tuple[str, str]:
    _, api_key, base_url, _ = _resolve_best_model()
    return api_key, base_url


def _resolve_model() -> str:
    model, _, _, _ = _resolve_best_model()
    return model


# ---------------------------------------------------------------------------
# Toolsets
# ---------------------------------------------------------------------------

def _disabled_toolsets() -> list[str] | None:
    """Tools too dangerous for a Telegram group bot.

    All other tools (web_search, web_extract, memory, session_search, skills,
    todo, clarify, delegate_task, text_to_speech, tool_search, etc.) are
    automatically available when this list is used as disabled_toolsets.

    Note: cronjob and kanban do NOT exist in hermes-agent v0.19.0.
    """
    return ["terminal", "execute_code", "write_file", "process", "patch"]


# ---------------------------------------------------------------------------
# Agent pool
# ---------------------------------------------------------------------------

_agent_pool: dict[str, Any] = {}
_agent_pool_lock = threading.Lock()


def _make_agent(system: str, session_key: str = ""):
    from run_agent import AIAgent

    model, api_key, base_url, provider = _resolve_best_model()
    disabled = _disabled_toolsets()

    if session_key and session_key in _agent_pool:
        cached = _agent_pool[session_key]
        cached.ephemeral_system_prompt = system
        return cached, model, base_url

    kwargs: dict[str, Any] = {
        "model": model,
        "quiet_mode": True,
        "skip_context_files": True,
        "skip_memory": False,
        "max_iterations": int(_env("HERMES_MAX_ITERATIONS") or "20"),
        "platform": "telegram",
        "load_soul_identity": True,
        "session_id": session_key or None,
    }

    if api_key:
        kwargs["api_key"] = api_key
    if base_url:
        kwargs["base_url"] = base_url
    if disabled:
        kwargs["disabled_toolsets"] = disabled

    kwargs["ephemeral_system_prompt"] = system

    fallback = _resolve_fallback_model()
    if fallback:
        kwargs["fallback_model"] = fallback

    agent = AIAgent(**kwargs)

    if session_key:
        with _agent_pool_lock:
            if len(_agent_pool) > 100:
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

    session_key = f"bob_{chat_id}_{user_id}"

    history = load_history(chat_id, user_id)
    model, _, _, _ = _resolve_best_model()
    meta: dict[str, Any] = {
        "provider": "hermes_native",
        "model": model,
        "engine": "hermes_native",
        "error": "",
    }

    if not hermes_available():
        meta["error"] = "run_agent.AIAgent not importable"
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

        result = agent.run_conversation(
            user_message=user_text,
            conversation_history=list(history) if history else None,
            system_message=system,
        )
        if isinstance(result, dict):
            reply = (result.get("final_response") or "").strip()
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

        if not history or history[-1].get("content") != reply:
            history = list(load_history(chat_id, user_id))
            history.append({"role": "user", "content": user_text})
            history.append({"role": "assistant", "content": reply})
        save_history(chat_id, user_id, history)

        # Record success for health tracking
        _record_success(model)

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

        # Record failure for health tracking
        _record_failure(meta.get("model", ""))

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
    model, _, base_url, _ = _resolve_best_model()
    s["sessions"] = session_count()
    s["soul_path"] = str(_SOUL_PATH)
    s["soul_loaded"] = _SOUL_PATH.is_file()
    s["hermes_home"] = _env("HERMES_HOME")
    s["hermes_agent_dir"] = _env("HERMES_AGENT_DIR") or "/opt/hermes-agent"
    s["hermes_import_ok"] = hermes_available()
    s["model"] = model
    s["fallback_model"] = _env("FALLBACK_MODEL_1") or "big-pickle"
    s["api_key_set"] = bool(_env("NVIDIA_API_KEY") or _env("OPENCODE_API_KEY") or _env("GEMINI_API_KEY"))
    s["base_url"] = base_url
    s["toolsets"] = ["ALL (except: " + ", ".join(_disabled_toolsets() or []) + ")"]
    s["memory_enabled"] = True
    s["agent_pool_size"] = len(_agent_pool)
    s["age_days"] = max(0.0, (time.time() - s.get("born", time.time())) / 86400.0)

    # Model health report
    health = _get_health_report()
    s["model_health"] = {}
    chain = _build_model_chain()
    seen_models = set()
    for entry in chain:
        m = entry["model"]
        if m in seen_models:
            continue
        seen_models.add(m)
        mh = health.get(m, {})
        s["model_health"][m] = {
            "failures": mh.get("failures", 0),
            "cooldown_until": mh.get("cooldown_until", 0),
            "healthy": _is_model_healthy(m),
            "last_success": mh.get("last_success", 0),
        }
    s["last_working_model"] = health.get("_last_working", "—")

    # Provider presence
    s["providers"] = []
    if _env("OPENCODE_ZEN_API_KEY") or _env("OPENCODE_API_KEY") or _env("OPENCODE_API_KEYS"):
        keys = _split(_env("OPENCODE_API_KEYS") or _env("OPENCODE_API_KEY") or _env("OPENCODE_ZEN_API_KEY"))
        s["providers"].append({
            "name": "opencode_zen",
            "models": _split(_env("OPENCODE_MODELS") or "big-pickle,north-mini-code-free"),
            "keys": len(keys),
            "base": _env("OPENCODE_BASE_URL") or "https://opencode.ai/zen/v1",
        })
    if _env("GEMINI_API_KEY") or _env("GOOGLE_API_KEY"):
        s["providers"].append({
            "name": "gemini",
            "models": [_env("GEMINI_MODEL") or "gemini-2.0-flash"],
            "keys": 1,
            "base": "google",
        })
    if _env("NVIDIA_API_KEY"):
        s["providers"].append({
            "name": "nvidia",
            "models": _split(_env("NVIDIA_MODELS") or "z-ai/glm-5.2"),
            "keys": 1,
            "base": _env("NVIDIA_BASE_URL") or "https://integrate.api.nvidia.com/v1",
            "note": "blocked from EU sandbox",
        })
    return s


def ping_providers() -> list[dict[str, Any]]:
    """Live ping via real Hermes AIAgent."""
    results = []
    ok = hermes_available()
    model, _, _, _ = _resolve_best_model()
    entry = {
        "provider": "hermes_native",
        "model": model,
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
