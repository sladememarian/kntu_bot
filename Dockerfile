# KNTU Bot 25 + real NousResearch Hermes Agent as Bob's brain
# Hermes requires Python >=3.11,<3.14 -- use 3.12.
FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8091 \
    HERMES_AGENT_DIR=/opt/hermes-agent \
    HERMES_HOME=/app/hermes_home \
    PYTHONPATH=/opt/hermes-agent:/app \
    PATH=/opt/hermes-agent/.venv/bin:/usr/local/bin:/usr/bin:/bin

# System deps for Hermes + git clone + Chromium (browser automation)
RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates curl git gcc g++ make \
        # Chromium deps for Hermes browser tool (web research)
        chromium chromium-driver \
        fonts-liberation libnss3 libxss1 libasound2 \
        libatk-bridge2.0-0 libgtk-3-0 libgbm1 \
        xdg-utils wget \
    && rm -rf /var/lib/apt/lists/*

# uv (Hermes' supported installer)
COPY --from=ghcr.io/astral-sh/uv:0.11.6 /uv /usr/local/bin/uv

# --- Install real Hermes Agent (NousResearch) ---
# Docs: https://hermes-agent.nousresearch.com/docs/guides/python-library
ARG HERMES_GIT_REF=main
RUN git clone --depth 1 --branch "${HERMES_GIT_REF}" \
        https://github.com/NousResearch/hermes-agent.git ${HERMES_AGENT_DIR} \
    && cd ${HERMES_AGENT_DIR} \
    && UV_PYTHON=3.12 uv sync --no-dev \
    && UV_PYTHON=3.12 uv pip install -e .

# Bot Python deps into the same Hermes venv
COPY requirements.txt ./
RUN cd ${HERMES_AGENT_DIR} && UV_PYTHON=3.12 uv pip install -r /app/requirements.txt

# Install agent-browser for Hermes browser tool (web research)
RUN cd ${HERMES_AGENT_DIR} && UV_PYTHON=3.12 uv pip install agent-browser 2>/dev/null || \
    (npm install -g agent-browser 2>/dev/null && echo "agent-browser installed via npm") || \
    echo "agent-browser install skipped (web_extract still works)"

# App source
COPY . ./
RUN mkdir -p /app/data/bob_sessions /app/hermes /app/hermes_home \
    && chmod +x /app/docker/entrypoint.sh

EXPOSE 8091

# Health: config + real Hermes AIAgent importable
HEALTHCHECK --interval=30s --timeout=15s --start-period=60s --retries=4 \
    CMD python -c "import config; from run_agent import AIAgent; import handlers.bob_ai" || exit 1

ENTRYPOINT ["/app/docker/entrypoint.sh"]
