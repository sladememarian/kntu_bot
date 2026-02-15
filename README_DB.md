# Database Editing Guide

The bot stores all data in a single PostgreSQL JSONB row (`bot_store` table, `id=1`).
You can inspect and edit it using the `_edit_db.py` tool.

## Setup

Set the `DATABASE_URL` environment variable first:

```powershell
# PowerShell
$env:DATABASE_URL = "postgresql://postgres:UEHmmnhOmhhDyedURoOeagiriJwKIGre@mainline.proxy.rlwy.net:35268/railway"
```

```bash
# Linux / macOS
export DATABASE_URL="postgresql://postgres:UEHmmnhOmhhDyedURoOeagiriJwKIGre@mainline.proxy.rlwy.net:35268/railway"
```

## Commands

### Show all keys (overview)
```
python _edit_db.py
```
Prints all top-level keys with their types and sizes.

### List key names only
```
python _edit_db.py keys
```

### Get a specific key
```
python _edit_db.py get wallets
python _edit_db.py get ophelia_brain
```
Outputs the value as pretty-printed JSON.

### Set a key
```
python _edit_db.py set debug true
python _edit_db.py set my_key '{"hello": "world"}'
```
The value is parsed as JSON. If parsing fails, it's stored as a string.

### Delete a key
```
python _edit_db.py delete some_old_key
```

### Dump entire database to file
```
python _edit_db.py raw
```
Creates `db_dump.json` with all data.

### Load data from file (replaces everything!)
```
python _edit_db.py load db_dump.json
```
⚠️ This **replaces** the entire database content with the file's contents.

## Workflow: Edit a Specific Value

1. **Dump** the database:
   ```
   python _edit_db.py raw
   ```
2. **Open** `db_dump.json` in your editor
3. **Find and edit** the value you want to change
4. **Load** it back:
   ```
   python _edit_db.py load db_dump.json
   ```

## Common Keys

| Key | Type | Description |
|-----|------|-------------|
| `wallets` | dict | `{chat_id: {user_id: balance}}` |
| `inventory` | dict | `{chat_id: {user_id: [items]}}` |
| `stocks` | dict | User stock portfolios |
| `group_lang` | dict | `{chat_id: "fa"/"en"}` |
| `ophelia_brain` | dict | OPHELIA AI brain data |
| `markov_data` | dict | Markov AI chain data |
| `daily_claims` | dict | Daily reward claims |
| `jail` | dict | Jailed users & timestamps |
| `warns` | dict | User warnings |
| `purchase_counts` | dict | Item purchase history (inflation) |

## Example: Give Someone Money

```
python _edit_db.py raw
# Edit db_dump.json → wallets → chat_id → user_id → new balance
python _edit_db.py load db_dump.json
```

Or use `set` for a single key:
```
python _edit_db.py get wallets > wallets.json
# edit wallets.json
python _edit_db.py set wallets "$(cat wallets.json)"
```
