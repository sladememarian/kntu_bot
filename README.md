# 🤖 KNTU Bot 25

A fun, bilingual (Persian 🇮🇷 / English 🇬🇧) Telegram group bot with lots of features!

## ✨ Features

| Command | Description (FA) | Description (EN) |
|---------|------------------|-------------------|
| `/start` | شروع ربات | Start the bot |
| `/help` | راهنما | Help guide |
| `/ship` | شیپ کردن دو نفر 💕 | Ship two random members |
| `/lagab [لقب]` | لقب گذاشتن (ریپلای) 🏷 | Give nickname (reply) |
| `/joke` | جوک 😂 | Tell a joke |
| `/story` | داستان 📖 | Tell a story |
| `/news` | اخبار از کانال‌ها 📰 | News from channels |
| `/setnews [channel]` | اضافه کردن کانال خبری 📡 | Add news channel |
| `/removenews [channel]` | حذف کانال خبری 🗑 | Remove news channel |
| `/ai [سوال]` | چت با هوش مصنوعی 🧠 | Chat with AI |
| `/rizz` | نرخ ریز 😏 | Rizz rate |
| `/gay` | نرخ گی 🌈 | Gay rate |
| `/book` | پیشنهاد کتاب 📚 | Book suggestion |
| `/imagine [توضیح]` | ساخت تصویر 🎨 | Generate image |
| `/lang` | تغییر زبان 🌐 | Toggle language |
| `/debug` | حالت دیباگ 🔧 | Debug mode (admin only) |

## 🚀 Setup

### 1. Install Python 3.10+

### 2. Clone & Install Dependencies
```bash
cd telegram_bot
pip install -r requirements.txt
```

### 3. Configure Environment
```bash
# Copy the example env file
copy .env.example .env       # Windows
# cp .env.example .env       # Linux/Mac
```

Edit `.env` and fill in:
- **`BOT_TOKEN`** — Get from [@BotFather](https://t.me/BotFather) on Telegram
- **`OPENAI_API_KEY`** — Get from [OpenAI](https://platform.openai.com/api-keys) (for `/ai` and `/imagine`)
- **`ADMIN_IDS`** — Your Telegram user ID (get from [@userinfobot](https://t.me/userinfobot))

### 4. Run the Bot
```bash
python bot.py
```

### 5. Add to Group
1. Open [@BotFather](https://t.me/BotFather)
2. Send `/mybots` → select your bot → **Bot Settings** → **Allow Groups** → Turn ON
3. Also enable **Group Privacy** → Turn OFF (so bot can track members)
4. Add the bot to your group
5. Make it admin (recommended for full functionality)

## 📁 Project Structure

```
telegram_bot/
├── bot.py              # Main entry point
├── config.py           # Configuration loader
├── storage.py          # JSON-based data persistence
├── strings.py          # Bilingual strings (FA/EN)
├── requirements.txt    # Python dependencies
├── .env.example        # Environment template
├── .env                # Your secrets (not in git)
├── data.json           # Auto-generated data store
├── README.md           # This file
└── handlers/
    ├── __init__.py
    ├── general.py      # /start, /help, /lang, /debug
    ├── fun.py          # /ship, /lagab, /rizz, /gay
    ├── jokes_stories.py # /joke, /story
    ├── news.py         # /news, /setnews, /removenews
    ├── ai_chat.py      # /ai (OpenAI GPT)
    ├── books.py        # /book
    ├── image_gen.py    # /imagine (DALL·E)
    └── welcome.py      # Greet new members
```

## 🔧 Customization

### Adding More Jokes/Stories
Edit `handlers/jokes_stories.py` — add items to `JOKES["fa"]`, `JOKES["en"]`, `STORIES["fa"]`, `STORIES["en"]`.

### Adding More Books
Edit `handlers/books.py` — add items to `BOOKS["fa"]` or `BOOKS["en"]`.

### Changing Welcome Messages
Edit `strings.py` — modify `welcome_group` in either language.

### Debug Mode
Use `/debug` in chat (admin only) to toggle verbose error messages.

## 🛡️ Notes
- All data is stored locally in `data.json`
- The bot works without OpenAI API key — AI and image features will show an error message
- News feature links to channels; the bot must be added to channels to forward messages
- The bot auto-tracks members who send messages for the `/ship` feature

## 📜 License
Free for personal & university use. Made for KNTU 🎓
