FROM python:3.13-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8091

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . ./

# Ensure Bob session + hermes soul dirs exist
RUN mkdir -p /app/data/bob_sessions /app/hermes

EXPOSE 8091

# Lightweight liveness: verifies the app + config import cleanly.
HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD python -c "import config; import handlers.bob_ai; import handlers.hermes_brain" || exit 1

CMD ["python", "app.py"]
