# Bob = real Hermes Agent + Casino

## What Bob runs
Bob (`/bob`) uses the **real** [NousResearch Hermes Agent](https://github.com/NousResearch/hermes-agent)
`AIAgent` class from `run_agent.py` (installed into the Docker image at `/opt/hermes-agent`).

Not a reimplementation — the same library Hermes documents here:
https://hermes-agent.nousresearch.com/docs/guides/python-library

## Daytona `.env` (gitignored)
```bash
nano /home/kntu_bot/.env
```

```env
DISABLE_AIOHTTP_SERVER=false
PORT=8091
WEB_URL=https://8091-8365a2c3-5e86-45fc-bf95-6b58a1f6a309.daytonaproxy01.eu

# OpenCode — comma-separated, ONE line (first key → Hermes OPENCODE_ZEN_API_KEY)
OPENCODE_API_KEYS=sk-key1,sk-key2,sk-key3
OPENCODE_API_KEY=sk-key1
OPENCODE_BASE_URL=https://opencode.ai/zen/v1
OPENCODE_MODELS=north-mini-code-free,big-pickle

# Hermes
HERMES_MODEL=north-mini-code-free
HERMES_TOOLSETS=none
HERMES_MAX_ITERATIONS=12

# Optional NVIDIA (working inference key)
NVIDIA_API_KEY=nvapi-...
NVIDIA_BASE_URL=https://integrate.api.nvidia.com/v1
```

Then either wait for CI, or manually:
```bash
cd /home/kntu_bot
git pull --ff-only
docker rm -f kntu_bot25 2>/dev/null || true
docker compose down --remove-orphans
docker compose up -d --build --force-recreate
docker compose logs -f bot
```

Look for:
```
[entrypoint] real Hermes AIAgent: OK
```

Telegram:
- `/bobstats` → AIAgent import ✅
- `/bob who are you?` → Bob / Markov & Ophelia

## CI container-name conflict
Fixed: deploy workflow now `docker rm -f` stale names and `compose down` before recreate.
Compose no longer uses a fixed `container_name` for the bot.

## NVIDIA curl "nothing happened"
Always print status:
```bash
curl -sS -w "\nHTTP %{http_code}\n" https://integrate.api.nvidia.com/v1/chat/completions \
  -H "Authorization: Bearer $NVIDIA_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"deepseek-ai/deepseek-v4-flash","messages":[{"role":"user","content":"hi"}],"max_tokens":16}'
```
