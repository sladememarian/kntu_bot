# Bob Hermes + Casino deploy notes

## What changed
- `/bob` now uses a **Hermes-style brain** (`handlers/hermes_brain.py` + `hermes/SOUL.md`)
- `/bobstats` kept — shows providers, model, sessions
- Casino aiohttp server enabled on **port 8091**
- Telegram Play button can mint **Daytona signed preview URLs** when `DAYTONA_API_KEY` is set

## Sandbox `.env` (not in git)
On the Daytona VM after pull, ensure `/home/kntu_bot/.env` includes:

```bash
DISABLE_AIOHTTP_SERVER=false
PORT=8091
WEB_URL=https://8091-<sandboxId>.daytonaproxy01.eu

# Bob / Hermes providers
OPENCODE_API_KEY=...
OPENCODE_API_KEYS=key1,key2,key3
OPENCODE_BASE_URL=https://opencode.ai/zen/v1
OPENCODE_MODELS=north-mini-code-free,big-pickle

# Optional
NVIDIA_API_KEY=...
GEMINI_API_KEY=...

# Optional signed preview minting (recommended for Telegram WebView)
DAYTONA_API_KEY=dtn_...
DAYTONA_SANDBOX_ID=<sandbox id>
DAYTONA_SIGNED_EXPIRES=3600
```

Then:
```bash
cd /home/kntu_bot && git pull --ff-only && docker compose up -d --build && docker compose ps
docker compose logs --tail=50 bot
```

## Daytona "I Understand, Continue" warning
Per Daytona docs (https://www.daytona.io/docs/en/preview/):
- Browser interstitial is **by design** on preview hosts
- Fully skip only via:
  1. Header `X-Daytona-Skip-Preview-Warning: true` (not injectable by Telegram WebView)
  2. Org **Tier 3**
  3. **Custom preview proxy** on your own domain
- Signed preview URLs remove **auth** friction (Continue often looks broken when auth token is missing)
- Also set sandbox `public=true` in Daytona so previews don't require tokens

## Native full Hermes agent (optional later)
```bash
git clone https://github.com/NousResearch/hermes-agent.git /opt/hermes-agent
cd /opt/hermes-agent && curl -LsSf https://astral.sh/uv/install.sh | sh && uv sync
# in .env:
HERMES_HOME=/opt/hermes-agent
HERMES_MODEL=north-mini-code-free
HERMES_BASE_URL=https://opencode.ai/zen/v1
```

## Verify
- Telegram: `/bob who are you?` → Bob / Markov & Ophelia
- `/bobstats` → opencode provider listed
- `/casinogame` → Play opens game; wallet matches `/wallet`
