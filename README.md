# 🤖 KNTU Bot 25

A feature-packed, bilingual (Persian / English 🇬🇧) Telegram group bot — economy, gacha, clans, casino, AI, and 80+ commands to keep your group alive.

---

## 🏛️ Feature Overview

| System | Highlights |
|--------|-----------|
| 🎮 **Fun & Games** | Ship, XO, riddles, truth/dare, 8-ball, profile cards |
| 🎰 **Gacha** | Roll 141 mythology characters with portraits, trade & sell |
| 💰 **Economy** | Wallet, daily, work, fish, mine, quest, gambling, stocks, real estate |
| ⚔️ **Clans** | Create clans, deposit, war, leaderboards |
| 🛒 **Shops** | Clothing, pets, food, abilities, shields & landmines |
| 🏦 **Bank & Casino** | Loans, embezzle, heists, megaslots, blackjack, coinflip |
| 🧠 **AI** | LangChain Gemini agent, OPHELIA emotion AI, Markov chain |
| 🔧 **Tools** | Image gen, music search, books, anime, family tree, calendar |
| 🎁 **Drops** | Random cash bags every 80-150 messages |
| 🎯 **Bounties** | Place bounties on other players |

---

## 🎮 Commands

### Fun & Games
| Command | Description |
|---------|-------------|
| `/ship` | Ship two random members 💕 |
| `/lagab [nick]` | Set nickname (reply) |
| `/joke` | Tell a joke |
| `/story` | Short story |
| `/rizz` | Rizz rate 😏 |
| `/gay` | Gay rate 🌈 |
| `/truth` | Truth question |
| `/dare` | Dare challenge |
| `/xo` | Tic-tac-toe (reply) |
| `/riddle` | Riddle with cash reward (15/day) |
| `/8ball [question]` | Magic 8-ball |
| `/howmuch [question]` | Random percentage |
| `/whois [question]` | Who is? |
| `/quote` | Random quote |
| `/advice` | Random advice |
| `/profile` | Profile card with stats |

### 🎰 Gacha & Collection
| Command | Description |
|---------|-------------|
| `/roll` | Roll for a mythology character (5 rolls / 4 hours) |
| `/collection` | View your character collection |
| `/sellchar [name]` | Sell a character for coins |
| `/tradechar [name]` | Trade a character (reply) |

**141 characters** across 5 rarities:
- ⚪ Common (45%) — Anansi, Coyote, Sprite, Troll, Alchemist, Corsair, …
- 🟢 Uncommon (25%) — Hermes, Bastet, Medusa, Sphinx, Tiamat, Morpheus, …
- 🟣 Rare (18%) — Artemis, Loki, Poseidon, Hades, Vishnu, Achilles, …
- 🟣 Epic (9%) — Athena, Thor, Hercules, Prometheus, Rama, Surtr, …
- 🟡 Legendary (3%) — Zeus, Odin, Ra, Brahma, Kronos, Izanami

Each character has a unique portrait (local RPG art or **DiceBear** avatar).

### 💰 Economy
| Command | Description |
|---------|-------------|
| `/wallet` | Check balance |
| `/daily` | Daily reward (+ streak bonus!) |
| `/work` | Work & earn (1h cooldown) |
| `/spin` | Spin the wheel (8h cooldown) |
| `/fish` | Go fishing |
| `/mine` | Mine for resources |
| `/quest` | Daily quest |
| `/bet [amount]` | Coin flip bet |
| `/slots [amount]` | Slot machine |
| `/dice [odd/even] [amount]` | Dice roll |
| `/rps [r/p/s] [amount]` | Rock paper scissors |
| `/rob` | Rob someone (reply) |
| `/give [amount]` | Transfer coins (reply) |
| `/bounty [amount]` | Place bounty on someone (reply) |
| `/bounties` | View active bounties |
| `/invest [ticker] [qty]` | Buy stocks |
| `/sell [ticker] [qty]` | Sell stocks |
| `/portfolio` | Stock portfolio |
| `/profit` | Investment P&L |
| `/realestate` | Real estate market |
| `/buyproperty [type]` | Buy property |
| `/sellproperty [type]` | Sell property |
| `/event` | Daily world event |
| `/economy` | Economy status & taxes |
| `/jail` | Jailed members |
| `/leaderboard` | Richest members |
| `/donate [amount]` | Donate to charity |
| `/charity` | Charity leaderboard |

### ⚔️ Clans
| Command | Description |
|---------|-------------|
| `/clan create [name]` | Create a clan (5,000$) |
| `/clan join` | Join a clan (reply to member) |
| `/clan leave` | Leave your clan |
| `/clan info` | Clan stats |
| `/clan members` | Member list |
| `/clan deposit [amount]` | Deposit to clan bank |
| `/clan withdraw [amount]` | Withdraw (leader only) |
| `/clan war` | Declare war (reply to enemy clan member) |
| `/clan list` | All clans |

War power = members×10 + wins×3 + luck!

### 🛒 Shops
| Command | Description |
|---------|-------------|
| `/shop` | Clothing & accessories |
| `/buy [item]` | Buy an item |
| `/petshop` | Pet shop |
| `/buypet [pet]` | Buy a pet |
| `/foodshop` | Food shop |
| `/buyfood [food]` | Buy food |
| `/eat [food]` | Eat food |
| `/drink [drink]` | Drink |
| `/abilities` | Ability shop |
| `/buyability [ability]` | Buy an ability |
| `/inventory` | Your inventory |
| `/gift [item]` | Gift an item (reply) |

**Protection items** (from `/shop`):
- 🛡️ Shield (300$) — blocks robbery attempts
- 💣 Landmine (500$) — explodes the robber!

**Abilities** (usable in chat):
`/punch /hug /kiss /kill /slap /tickle /poke /bite /pat /highfive /revive`

### 🏦 Bank & Casino
| Command | Description |
|---------|-------------|
| `/bank [deposit/withdraw] [amount]` | Banking |
| `/loan [take/pay] [amount]` | Loans |
| `/bankmanager` | View bank manager |
| `/embezzle` | Embezzle funds (manager only) |
| `/investigate` | Investigate the manager |
| `/bankrob` | Rob the bank (4+ people) |
| `/bail` | Bail someone out (reply) |
| `/jailbreak` | Break out of jail (3+ reply) |
| `/casino` | Casino menu |
| `/megaslots [amount]` | 5-reel mega slots |
| `/blackjack [amount]` | Blackjack |
| `/coinflip [amount]` | Coin flip |
| `/bar` | Bar & drinks |
| `/casinoleader` | Casino boss |
| `/paytax` | Pay daily tax |
| `/casinogame` | HTML5 online game |

### 🧠 AI
| Command | Description |
|---------|-------------|
| `/ai [question]` | LangChain agent (Google Gemini) |
| `/ai3 [text]` | OPHELIA — emotion-based AI |
| `/ai3stats` | OPHELIA brain stats |

OPHELIA learns from group conversations and responds based on detected emotions.

### 🔧 Tools & Misc
| Command | Description |
|---------|-------------|
| `/imagine [desc]` | Generate image |
| `/music [name]` | Search & download music |
| `/book` | Book suggestion |
| `/anime` | Anime suggestion |
| `/movie` | Movie suggestion |
| `/game` | Game suggestion |
| `/news` | Latest news |
| `/family` | Family tree system |
| `/calendar` | Ancient calendar |
| `/places` | Browse locations |
| `/date [place]` | Go on a date (reply) |
| `/giftpet` | Gift a pet (reply) |
| `/giftfood` | Gift food (reply) |
| `warn` | Warn user (reply, admin only) |
| `/lang` | Toggle FA ↔ EN |
| `/debug` | Debug mode (admin only) |

---

## 🚀 Setup

### 1. Install Python 3.10+

### 2. Clone & Install Dependencies
```bash
cd telegram_bot
pip install -r requirements.txt
```

### 3. Configure Environment Variables
| Variable | Required | Description |
|----------|----------|-------------|
| `BOT_TOKEN` | ✅ | From [@BotFather](https://t.me/BotFather) |
| `GOOGLE_API_KEY` | ✅ | Google AI Studio key (for `/ai`, `/imagine`) |
| `DATABASE_URL` | ⬜ | PostgreSQL URL (falls back to JSON) |
| `ADMIN_IDS` | ⬜ | Comma-separated Telegram user IDs |

### 4. Run the Bot
```bash
python app.py
```

### 5. Add to Group
1. Open [@BotFather](https://t.me/BotFather) → `/mybots` → select your bot
2. **Bot Settings** → **Allow Groups** → Turn ON
3. **Group Privacy** → Turn OFF (so bot can track members)
4. Add the bot to your group and make it admin

---

## 📁 Project Structure

```
telegram_bot/
├── app.py                  # Entry point — registers all handlers
├── config.py               # Environment config loader
├── storage.py              # PostgreSQL + JSON data layer
├── strings.py              # Bilingual strings (FA/EN)
├── requirements.txt        # Python dependencies
├── data.json               # Local JSON fallback store
├── Dockerfile              # Railway deployment
├── static/
│   └── casino.html         # HTML5 casino game
└── handlers/
    ├── __init__.py
    ├── general.py           # /start, /help, /lang, /debug
    ├── fun.py               # /ship, /lagab, /rizz, /gay, /truth, /dare
    ├── jokes_stories.py     # /joke, /story
    ├── news.py              # /news
    ├── ai_chat.py           # /ai (LangChain + Gemini)
    ├── ophelia_ai.py        # /ai3 (OPHELIA emotion AI)
    ├── markov_ai.py         # Markov chain passive listener
    ├── gacha.py             # /roll, /collection, /sellchar, /tradechar
    ├── clan.py              # /clan (create/join/war/deposit/etc.)
    ├── drops.py             # Random cash drop system
    ├── economy.py           # Full economy + gambling + stocks + bounties
    ├── shop.py              # Clothing shop + protection items
    ├── petshop.py           # Pet shop
    ├── foodshop.py          # Food shop
    ├── abilities.py         # Ability shop + combat commands
    ├── bank.py              # Bank, loans, heists
    ├── casino.py            # Casino games (megaslots, blackjack, etc.)
    ├── family.py            # Family tree system
    ├── books.py             # /book, /anime, /movie, /game
    ├── image_gen.py         # /imagine
    ├── music.py             # /music
    ├── calendar.py          # /calendar
    ├── places.py            # /places, /date
    ├── howallbot.py         # /profile (enhanced profile card)
    ├── riddle.py            # /riddle
    ├── xo.py               # /xo (tic-tac-toe)
    ├── tools.py             # /8ball, /howmuch, /whois, /quote, /advice
    ├── suggest.py           # /suggest
    ├── welcome.py           # Greet new members
    └── pixel_art.py         # Pixel art generator
```

---

## 🛡️ Notes
- Data is stored in PostgreSQL (Railway) with automatic JSON fallback
- The bot works without `GOOGLE_API_KEY` — AI features will show an error
- Economy uses dynamic supply & demand pricing
- Random cash drops keep groups engaged (every 80-150 messages)
- The bot auto-tracks members who send messages

## 📜 License
Free for personal & university use. Made for KNTU 🎓
