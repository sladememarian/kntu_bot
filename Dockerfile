FROM python:3.13-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . ./

# Lightweight liveness: verifies the app + config import cleanly.
# (docker compose defines a richer healthcheck that also checks Mongo.)
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD python -c "import config" || exit 1

CMD ["python", "app.py"]
