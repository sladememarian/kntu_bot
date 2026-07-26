# ==========================================
# Hermes-compatible brain for Bob
# ==========================================
# Uses OpenAI-compatible Chat Completions APIs (same wire format Hermes
# uses via base_url/api_key). Provider chain:
#   1) OpenCode Zen  (primary — free models like north-mini-code-free / big-pickle)
#   2) NVIDIA integrate.api.nvidia.com
#   3) OpenAI-compatible custom (OPENAI_BASE_URL)
#   4) Google Gemini (google-genai), if available
#
# Optional: if HERMES_HOME points at a NousResearch/hermes-agent checkout
# with run_agent.AIAgent importable, that path is preferred.
# ==========================================

from __future__ import annotations

import json
import logging
import os
import threading
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
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
    "born": time.time(),
    "sessions": 0,
}


def _env(name: str, default: str = "") -> str:
    return (os.environ.get(name) or default).strip()


def _split_keys(raw: str) -> list[str]:
    if not raw:
        return []
    parts = []
    for chunk in raw.replace("\n", ",").split(","):
        c = chunk.strip()
        if c:
            parts.append(c)
    return parts


@dataclass
class Provider:
    name: str
    base_url: str
    api_keys: list[str]
    models: list[str]
    extra_headers: dict[str, str] = field(default_factory=dict)


def _providers() -> list[Provider]:
    out: list[Provider] = []

    oc_keys = _split_keys(_env("OPENCODE_API_KEYS") or _env("OPENCODE_API_KEY"))
    oc_models = _split_keys(
        _env("OPENCODE_MODELS") or "north-mini-code-free,big-pickle"
    )
    if oc_keys:
        out.append(
            Provider(
                name="opencode",
                base_url=_env("OPENCODE_BASE_URL") or "https://opencode.ai/zen/v1",
                api_keys=oc_keys,
                models=oc_models,
                extra_headers={"User-Agent": "kntu-bob-hermes/1.0"},
            )
        )

    nv_key = _env("NVIDIA_API_KEY")
    nv_models = _split_keys(
        _env("NVIDIA_MODELS")
        or "google/gemma-4-31b-it,deepseek-ai/deepseek-v4-flash,deepseek-ai/deepseek-v4-pro,z-ai/glm-5.2,thinkingmachines/inkling,nvidia/ising-calibration-1.5-31b"
    )
    if nv_key:
        out.append(
            Provider(
                name="nvidia",
                base_url=_env("NVIDIA_BASE_URL") or "https://integrate.api.nvidia.com/v1",
                api_keys=[nv_key],
                models=nv_models,
            )
        )

    oa_key = _env("OPENAI_API_KEY") or _env("THINKINGMACHINES_API_KEY")
    oa_base = _env("OPENAI_BASE_URL") or _env("THINKINGMACHINES_BASE_URL")
    oa_models = _split_keys(_env("OPENAI_MODELS") or _env("THINKINGMACHINES_MODEL") or "")
    if oa_key and oa_base:
        out.append(
            Provider(
                name="openai_compat",
                base_url=oa_base.rstrip("/"),
                api_keys=[oa_key],
                models=oa_models or ["default"],
            )
        )

    return out


def load_soul() -> str:
    try:
        if _SOUL_PATH.is_file():
            return _SOUL_PATH.read_text(encoding="utf-8").strip()
    except Exception as e:
        logger.warning("SOUL.md read failed: %s", e)
    return (
        "You are Bob (باب), the group AI of KNTU Bot 25. "
        "You are the son of Markov and Ophelia. "
        "Be helpful, witty, bilingual (Persian + English), and concise. "
        "Never claim to be a different product name in public — users call you Bob."
    )


def _session_path(chat_id: int, user_id: int) -> Path:
    return _SESSIONS_DIR / f"{chat_id}_{user_id}.json"


def load_history(chat_id: int, user_id: int, limit: int = 24) -> list[dict]:
    path = _session_path(chat_id, user_id)
    if not path.is_file():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        msgs = data.get("messages") or []
        return msgs[-limit:]
    except Exception:
        return []


def save_history(chat_id: int, user_id: int, messages: list[dict], max_keep: int = 40):
    path = _session_path(chat_id, user_id)
    payload = {
        "messages": messages[-max_keep:],
        "updated": time.time(),
    }
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=0), encoding="utf-8")
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


def _http_json(url: str, headers: dict, payload: dict, timeout: int = 90) -> dict:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")[:500]
        raise RuntimeError(f"HTTP {e.code}: {body}") from e


def _openai_chat(
    base_url: str,
    api_key: str,
    model: str,
    messages: list[dict],
    extra_headers: dict | None = None,
    max_tokens: int = 512,
    temperature: float = 0.8,
) -> str:
    url = base_url.rstrip("/") + "/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    if extra_headers:
        headers.update(extra_headers)
    payload = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "stream": False,
    }
    data = _http_json(url, headers, payload)
    choices = data.get("choices") or []
    if not choices:
        raise RuntimeError(f"empty choices: {str(data)[:200]}")
    msg = choices[0].get("message") or {}
    content = msg.get("content")
    if isinstance(content, list):
        # some providers return content parts
        parts = []
        for p in content:
            if isinstance(p, dict) and p.get("type") == "text":
                parts.append(p.get("text") or "")
            elif isinstance(p, str):
                parts.append(p)
        content = "".join(parts)
    text = str(content or "").strip()
    if not text:
        # some gateways put text under different keys
        alt = choices[0].get("text") or data.get("output_text") or ""
        text = str(alt).strip()
    if not text:
        raise RuntimeError("empty content")
    return text


def _try_native_hermes(messages: list[dict], system: str) -> str | None:
    """Prefer real Nous Hermes AIAgent when HERMES_HOME is configured."""
    home = _env("HERMES_HOME")
    if not home:
        return None
    import sys

    if home not in sys.path:
        sys.path.insert(0, home)
    try:
        from run_agent import AIAgent  # type: ignore
    except Exception as e:
        logger.info("Native Hermes not importable: %s", e)
        return None

    model = _env("HERMES_MODEL") or _env("OPENCODE_MODELS", "north-mini-code-free").split(",")[0]
    api_key = (
        _env("OPENCODE_API_KEY")
        or (_split_keys(_env("OPENCODE_API_KEYS")) or [""])[0]
        or _env("OPENAI_API_KEY")
        or _env("NVIDIA_API_KEY")
    )
    base_url = (
        _env("HERMES_BASE_URL")
        or _env("OPENCODE_BASE_URL")
        or "https://opencode.ai/zen/v1"
    )
    # Build user message from last user turn; feed history via conversation_history
    user_msg = ""
    history = []
    for m in messages:
        if m["role"] == "system":
            continue
        history.append(m)
    if history and history[-1]["role"] == "user":
        user_msg = history[-1]["content"]
        history = history[:-1]
    else:
        user_msg = "Hello"
        history = []

    agent = AIAgent(
        model=model,
        quiet_mode=True,
        skip_context_files=True,
        skip_memory=True,
        max_iterations=int(_env("HERMES_MAX_ITERATIONS") or "12"),
        api_key=api_key or None,
        base_url=base_url,
        platform="telegram",
        ephemeral_system_prompt=system,
        enabled_toolsets=_split_keys(_env("HERMES_TOOLSETS")) or None,
    )
    result = agent.run_conversation(
        user_message=user_msg,
        conversation_history=history or None,
        system_message=system,
    )
    if isinstance(result, dict):
        return (result.get("final_response") or "").strip() or None
    return str(result).strip() or None


def _try_gemini(messages: list[dict], system: str) -> str | None:
    key = _env("GEMINI_API_KEY") or _env("GOOGLE_API_KEY")
    if not key:
        return None
    try:
        from google import genai
        from google.genai import types
    except Exception:
        return None
    model = _env("GEMINI_MODEL") or "gemini-2.0-flash"
    try:
        client = genai.Client(api_key=key)
        # flatten to single prompt with roles
        lines = [f"[system]\n{system}"]
        for m in messages:
            if m["role"] == "system":
                continue
            lines.append(f"[{m['role']}]\n{m['content']}")
        prompt = "\n\n".join(lines) + "\n\n[assistant]\n"
        resp = client.models.generate_content(model=model, contents=prompt)
        text = getattr(resp, "text", None) or ""
        return text.strip() or None
    except Exception as e:
        logger.warning("Gemini failed: %s", e)
        return None


def chat(
    *,
    chat_id: int,
    user_id: int,
    user_text: str,
    lang: str = "fa",
    user_name: str = "",
) -> tuple[str, dict[str, Any]]:
    """
    Run one Hermes-style turn. Returns (reply_text, meta).
    """
    system = load_soul()
    if lang == "fa":
        system += (
            "\n\nLanguage: Prefer Persian (Farsi) when the user writes Persian; "
            "match the user's language. Keep replies Telegram-friendly (short paragraphs)."
        )
    else:
        system += "\n\nLanguage: Prefer English unless the user writes another language."
    if user_name:
        system += f"\n\nYou are talking to: {user_name}."

    history = load_history(chat_id, user_id)
    messages: list[dict] = [{"role": "system", "content": system}]
    messages.extend(history)
    messages.append({"role": "user", "content": user_text})

    meta: dict[str, Any] = {"provider": "", "model": "", "error": ""}
    reply: str | None = None

    # 1) Native Hermes if available
    try:
        reply = _try_native_hermes(messages, system)
        if reply:
            meta["provider"] = "hermes_native"
            meta["model"] = _env("HERMES_MODEL") or "hermes"
    except Exception as e:
        logger.warning("Native Hermes path failed: %s", e)
        meta["error"] = str(e)[:200]

    # 2) Provider chain (OpenAI-compatible — Hermes wire format)
    if not reply:
        last_err = ""
        for prov in _providers():
            for model in prov.models:
                for key in prov.api_keys:
                    try:
                        reply = _openai_chat(
                            prov.base_url,
                            key,
                            model,
                            messages,
                            extra_headers=prov.extra_headers,
                            max_tokens=int(_env("BOB_MAX_TOKENS") or "512"),
                            temperature=float(_env("BOB_TEMPERATURE") or "0.8"),
                        )
                        meta["provider"] = prov.name
                        meta["model"] = model
                        break
                    except Exception as e:
                        last_err = f"{prov.name}/{model}: {e}"
                        logger.info("provider miss %s", last_err)
                        continue
                if reply:
                    break
            if reply:
                break
        if not reply:
            meta["error"] = last_err[:300]

    # 3) Gemini fallback
    if not reply:
        g = _try_gemini(messages, system)
        if g:
            reply = g
            meta["provider"] = "gemini"
            meta["model"] = _env("GEMINI_MODEL") or "gemini-2.0-flash"

    with _lock:
        _stats["calls"] += 1
        if reply:
            _stats["provider_last"] = meta.get("provider") or ""
            _stats["model_last"] = meta.get("model") or ""
        else:
            _stats["errors"] += 1
        _stats["sessions"] = session_count()

    if not reply:
        if lang == "fa":
            reply = "مغزم الان offline-e 🤖 — کلید API یا مدل رو چک کن (/bobstats)."
        else:
            reply = "My brain is offline 🤖 — check API keys/models (/bobstats)."
        meta["provider"] = meta.get("provider") or "none"

    # persist history (no system spam)
    new_hist = list(history)
    new_hist.append({"role": "user", "content": user_text})
    new_hist.append({"role": "assistant", "content": reply})
    try:
        save_history(chat_id, user_id, new_hist)
    except Exception as e:
        logger.warning("session save failed: %s", e)

    return reply, meta


def get_stats() -> dict[str, Any]:
    with _lock:
        s = dict(_stats)
    s["sessions"] = session_count()
    s["soul_path"] = str(_SOUL_PATH)
    s["soul_loaded"] = _SOUL_PATH.is_file()
    s["providers"] = [
        {"name": p.name, "models": p.models, "keys": len(p.api_keys), "base": p.base_url}
        for p in _providers()
    ]
    s["hermes_home"] = _env("HERMES_HOME")
    s["age_days"] = max(0.0, (time.time() - s.get("born", time.time())) / 86400.0)
    return s


def ping_providers() -> list[dict[str, Any]]:
    """Lightweight connectivity check for /bobstats and tests."""
    results = []
    probe_messages = [
        {"role": "system", "content": "Reply with exactly: pong"},
        {"role": "user", "content": "ping"},
    ]
    for prov in _providers():
        model = prov.models[0] if prov.models else ""
        key = prov.api_keys[0] if prov.api_keys else ""
        entry = {"provider": prov.name, "model": model, "ok": False, "error": ""}
        if not key or not model:
            entry["error"] = "missing key/model"
            results.append(entry)
            continue
        try:
            text = _openai_chat(
                prov.base_url,
                key,
                model,
                probe_messages,
                extra_headers=prov.extra_headers,
                max_tokens=32,
                temperature=0,
            )
            entry["ok"] = bool(text)
            entry["sample"] = (text or "")[:80]
            if not text:
                entry["error"] = "empty content"
        except Exception as e:
            entry["error"] = str(e)[:200]
        results.append(entry)
    return results
