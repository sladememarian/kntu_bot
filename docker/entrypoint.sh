#!/bin/sh
# Map bot env vars -> real Hermes Agent provider env vars, then start the bot.
set -eu

export HERMES_HOME="${HERMES_HOME:-/app/hermes_home}"
export HERMES_AGENT_DIR="${HERMES_AGENT_DIR:-/opt/hermes-agent}"
mkdir -p "$HERMES_HOME" "$HERMES_HOME/memories" "$HERMES_HOME/sessions" /app/data/bob_sessions

# --- NVIDIA (primary provider) ---
# NVIDIA_API_KEY + NVIDIA_BASE_URL are already read by Hermes via env passthrough.

# --- OpenCode Zen (fallback provider) ---
# Accept OPENCODE_API_KEY / OPENCODE_API_KEYS and map to Hermes' OPENCODE_ZEN_* names.
if [ -z "${OPENCODE_ZEN_API_KEY:-}" ]; then
  if [ -n "${OPENCODE_API_KEY:-}" ]; then
    export OPENCODE_ZEN_API_KEY="$OPENCODE_API_KEY"
  elif [ -n "${OPENCODE_API_KEYS:-}" ]; then
    # first key before comma
    export OPENCODE_ZEN_API_KEY="$(printf '%s' "$OPENCODE_API_KEYS" | cut -d, -f1 | tr -d ' ')"
  fi
fi
if [ -z "${OPENCODE_ZEN_BASE_URL:-}" ]; then
  export OPENCODE_ZEN_BASE_URL="${OPENCODE_BASE_URL:-https://opencode.ai/zen/v1}"
fi

# Also expose as generic OpenAI-compat for fallback_model
if [ -n "${OPENCODE_ZEN_API_KEY:-}" ]; then
  export OPENAI_API_KEY="${OPENAI_API_KEY:-$OPENCODE_ZEN_API_KEY}"
  export OPENAI_BASE_URL="${OPENAI_BASE_URL:-$OPENCODE_ZEN_BASE_URL}"
fi

# --- Gemini aliases ---
if [ -n "${GEMINI_API_KEY:-}" ] && [ -z "${GOOGLE_API_KEY:-}" ]; then
  export GOOGLE_API_KEY="$GEMINI_API_KEY"
fi

# --- Bob SOUL.md into HERMES_HOME ---
if [ -f /app/hermes/SOUL.md ]; then
  cp -f /app/hermes/SOUL.md "$HERMES_HOME/SOUL.md"
fi

# --- Hermes config (minimal, agent handles the rest) ---
if [ ! -f "$HERMES_HOME/config.yaml" ]; then
  cat > "$HERMES_HOME/config.yaml" <<EOF
model:
  default: ${HERMES_MODEL:-z-ai/glm-5.2}
  provider: nvidia
terminal:
  backend: local
EOF
fi

# --- Chromium path for browser tool ---
if command -v chromium >/dev/null 2>&1; then
  export CHROME_BIN="$(command -v chromium)"
  export CHROMIUM_BIN="$CHROME_BIN"
fi

# --- Ensure Hermes is on PYTHONPATH ---
export PYTHONPATH="${HERMES_AGENT_DIR}:${PYTHONPATH:-}"
export PATH="${HERMES_AGENT_DIR}/.venv/bin:${PATH:-}"

# --- Sanity log (no secrets) ---
echo "[entrypoint] HERMES_HOME=$HERMES_HOME"
echo "[entrypoint] HERMES_AGENT_DIR=$HERMES_AGENT_DIR"
if [ -n "${NVIDIA_API_KEY:-}" ]; then
  echo "[entrypoint] NVIDIA_API_KEY=set (primary provider)"
fi
if [ -n "${OPENCODE_ZEN_API_KEY:-}" ]; then
  echo "[entrypoint] OPENCODE_ZEN_API_KEY=set (fallback provider)"
fi
if [ -n "${GEMINI_API_KEY:-}" ]; then
  echo "[entrypoint] GEMINI_API_KEY=set (fallback provider)"
fi
if [ -n "${HERMES_TOOLSETS:-}" ]; then
  echo "[entrypoint] HERMES_TOOLSETS=$HERMES_TOOLSETS"
fi
if python -c "import run_agent; from run_agent import AIAgent" 2>/dev/null; then
  echo "[entrypoint] real Hermes AIAgent: OK"
else
  echo "[entrypoint] WARN: real Hermes AIAgent import failed"
fi

exec python app.py
