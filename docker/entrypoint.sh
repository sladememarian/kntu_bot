#!/bin/sh
# Map bot env vars → real Hermes Agent provider env vars, then start the bot.
set -eu

export HERMES_HOME="${HERMES_HOME:-/app/hermes_home}"
export HERMES_AGENT_DIR="${HERMES_AGENT_DIR:-/opt/hermes-agent}"
mkdir -p "$HERMES_HOME" "$HERMES_HOME/memories" "$HERMES_HOME/sessions" /app/data/bob_sessions

# --- OpenCode Zen (native Hermes provider) ---
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

# Also expose as generic OpenAI-compat for AIAgent(base_url=..., api_key=...)
if [ -n "${OPENCODE_ZEN_API_KEY:-}" ]; then
  export OPENAI_API_KEY="${OPENAI_API_KEY:-$OPENCODE_ZEN_API_KEY}"
  export OPENAI_BASE_URL="${OPENAI_BASE_URL:-$OPENCODE_ZEN_BASE_URL}"
fi

# NVIDIA → optional OpenAI-compat fallback (if user wants Hermes to hit NVIDIA directly)
if [ -n "${NVIDIA_API_KEY:-}" ] && [ -z "${OPENAI_API_KEY:-}" ]; then
  export OPENAI_API_KEY="$NVIDIA_API_KEY"
  export OPENAI_BASE_URL="${NVIDIA_BASE_URL:-https://integrate.api.nvidia.com/v1}"
fi

# Gemini aliases Hermes already understands
if [ -n "${GEMINI_API_KEY:-}" ] && [ -z "${GOOGLE_API_KEY:-}" ]; then
  export GOOGLE_API_KEY="$GEMINI_API_KEY"
fi

# Bob SOUL.md into HERMES_HOME (Hermes reads this as identity slot #1)
if [ -f /app/hermes/SOUL.md ]; then
  cp -f /app/hermes/SOUL.md "$HERMES_HOME/SOUL.md"
fi

# Minimal Hermes config if missing
if [ ! -f "$HERMES_HOME/config.yaml" ]; then
  MODEL="${HERMES_MODEL:-${OPENCODE_MODELS:-north-mini-code-free}}"
  # first model if comma-list
  MODEL="$(printf '%s' "$MODEL" | cut -d, -f1 | tr -d ' ')"
  cat > "$HERMES_HOME/config.yaml" <<EOF
model:
  default: ${MODEL}
  provider: opencode_zen
terminal:
  backend: local
EOF
fi

# Ensure Hermes is on PYTHONPATH
export PYTHONPATH="${HERMES_AGENT_DIR}:${PYTHONPATH:-}"
export PATH="${HERMES_AGENT_DIR}/.venv/bin:${PATH:-}"

# Sanity log (no secrets)
echo "[entrypoint] HERMES_HOME=$HERMES_HOME"
echo "[entrypoint] HERMES_AGENT_DIR=$HERMES_AGENT_DIR"
if [ -n "${OPENCODE_ZEN_API_KEY:-}" ]; then
  echo "[entrypoint] OPENCODE_ZEN_API_KEY=set"
else
  echo "[entrypoint] WARN: OPENCODE_ZEN_API_KEY not set — Bob/Hermes may be offline"
fi
if python -c "import run_agent; from run_agent import AIAgent" 2>/dev/null; then
  echo "[entrypoint] real Hermes AIAgent: OK"
else
  echo "[entrypoint] WARN: real Hermes AIAgent import failed"
fi

exec python app.py
