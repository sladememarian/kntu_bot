# ==========================================
# KNTU Bot 25 — Bank System
# ==========================================

import random
import io
import os
from datetime import datetime, date, timedelta

from telegram import Update
from telegram.ext import ContextTypes
from PIL import Image, ImageDraw, ImageFont

from storage import (
    get_lang, get_balance, add_balance, set_balance,
    load_data, save_data,
    get_user_name, set_user_name,
    get_stocks, set_stocks,
    get_jail_time, set_jail_time,
)
from config import ADMIN_IDS

# ── Constants ──────────────────────────────────────────────
KOLLAR = "کلار $"
INTEREST_RATE = 0.02          # 2 % daily
LOAN_MAX = 2000
LOAN_INTEREST = 0.10          # 10 %
LOAN_PENALTY_HOURS = 24
LOAN_PENALTY_RATE = 0.20      # 20 % extra
MANAGER_DURATION = 86400      # 24 h
MANAGER_BONUS_RATE = 0.05     # 5 %
EMBEZZLE_AMOUNT = 500
EMBEZZLE_SUCCESS_CHANCE = 0.30
INVESTIGATE_COST = 100
INVESTIGATE_SUCCESS_CHANCE = 0.20
JAIL_DURATION_EMBEZZLE = 21600  # 6 hours

# ── Image palette (same as the rest of the bot) ───────────
BG_COLOR = (30, 30, 46)
BOX_FILL = (69, 71, 90)
TEXT_COLOR = (205, 214, 244)
TITLE_COLOR = (137, 180, 250)
PRICE_COLOR = (166, 227, 161)


# ── Helpers ────────────────────────────────────────────────
def _remember_user(chat_id, user):
    set_user_name(chat_id, user.id,
                  (user.full_name or user.first_name or "User").strip())


def _get_font(size: int) -> ImageFont.FreeTypeFont:
    for p in [
        "C:\\Windows\\Fonts\\tahoma.ttf",
        "C:\\Windows\\Fonts\\arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]:
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def _now() -> datetime:
    return datetime.utcnow()


# ── Data accessors (bank_accounts / loans / bank_managers) ─
def _get_bank_account(data: dict, cid: str, uid: str) -> dict:
    return data.setdefault("bank_accounts", {}).setdefault(cid, {}).get(uid, {})


def _set_bank_account(data: dict, cid: str, uid: str, acc: dict):
    data.setdefault("bank_accounts", {}).setdefault(cid, {})[uid] = acc


def _get_loan(data: dict, cid: str, uid: str) -> dict:
    return data.setdefault("loans", {}).setdefault(cid, {}).get(uid, {})


def _set_loan(data: dict, cid: str, uid: str, loan: dict):
    data.setdefault("loans", {}).setdefault(cid, {})[uid] = loan


def _del_loan(data: dict, cid: str, uid: str):
    data.setdefault("loans", {}).setdefault(cid, {}).pop(uid, None)


def _get_manager(data: dict, cid: str) -> dict:
    return data.setdefault("bank_managers", {}).get(cid, {})


def _set_manager(data: dict, cid: str, mgr: dict):
    data.setdefault("bank_managers", {})[cid] = mgr


# ── Interest calculation ───────────────────────────────────
def _apply_interest(acc: dict) -> dict:
    """Apply pending daily interest to a bank account dict (in-place)."""
    if not acc or acc.get("balance", 0) <= 0:
        return acc
    last_str = acc.get("last_interest", "")
    if not last_str:
        acc["last_interest"] = _now().isoformat()
        return acc
    try:
        last_dt = datetime.fromisoformat(last_str)
    except ValueError:
        acc["last_interest"] = _now().isoformat()
        return acc
    days = (_now() - last_dt).total_seconds() / 86400.0
    if days >= 1:
        full_days = int(days)
        acc["balance"] = int(acc["balance"] * (1 + INTEREST_RATE) ** full_days)
        acc["last_interest"] = _now().isoformat()
    return acc


# ── Jail helper (same format as economy.py) ────────────────
def _check_jail(chat_id: int, user_id: int) -> int | None:
    """Return remaining seconds in jail or None if free."""
    jt = get_jail_time(chat_id, user_id)
    if not jt:
        return None
    duration = 360  # default
    ts = jt
    if "|" in jt:
        ts, dur_str = jt.rsplit("|", 1)
        try:
            duration = int(dur_str)
        except ValueError:
            pass
    try:
        jail_dt = datetime.fromisoformat(ts)
    except ValueError:
        return None
    diff = (_now() - jail_dt).total_seconds()
    if diff >= duration:
        return None
    return int(duration - diff)


# ── Markov "police report" helper ──────────────────────────
def _police_report(lang: str) -> str:
    """Try to generate a Markov-based police report; fall back to a canned one."""
    try:
        from handlers.markov_ai import generate
        text = generate(seed="police" if lang == "en" else "پلیس", max_words=25)
        if text:
            return text
    except Exception:
        pass
    if lang == "fa":
        return random.choice([
            "متهم در حین فرار از صحنه جرم دستگیر شد.",
            "مدارک اختلاس در کیف مدیر بانک پیدا شد.",
            "بازرس ویژه پرونده اختلاس را تایید کرد.",
            "شاهدان عینی متهم را در حال انتقال وجوه دیدند.",
        ])
    return random.choice([
        "Suspect was apprehended while fleeing the scene.",
        "Embezzlement documents were found in the manager's briefcase.",
        "Special investigator confirmed the embezzlement case.",
        "Witnesses saw the suspect transferring funds illegally.",
    ])


# ── Bank status image renderer ─────────────────────────────
def _render_bank_card(
    lang: str,
    user_name: str,
    wallet_bal: int,
    bank_bal: int,
    interest: str,
    loan_amount: int,
    manager_name: str,
) -> io.BytesIO:
    W, H = 460, 340
    font = _get_font(16)
    font_title = _get_font(22)
    font_sm = _get_font(13)

    img = Image.new("RGB", (W, H), BG_COLOR)
    draw = ImageDraw.Draw(img)

    # Title bar
    draw.rounded_rectangle([0, 0, W, 48], radius=12, fill=(49, 50, 68))
    title = "🏦 بانک مرکزی" if lang == "fa" else "🏦 Central Bank"
    tb = draw.textbbox((0, 0), title, font=font_title)
    draw.text(((W - tb[2] + tb[0]) // 2, 10), title, fill=TITLE_COLOR, font=font_title)

    rows = [
        ("👤", ("نام: " if lang == "fa" else "Name: ") + user_name, TEXT_COLOR),
        ("💰", ("کیف پول: " if lang == "fa" else "Wallet: ") + f"{wallet_bal}$", TEXT_COLOR),
        ("🏦", ("موجودی بانک: " if lang == "fa" else "Bank Balance: ") + f"{bank_bal}$", PRICE_COLOR),
        ("📈", ("نرخ سود: " if lang == "fa" else "Interest: ") + interest, TITLE_COLOR),
        ("📋", ("وام فعال: " if lang == "fa" else "Active Loan: ") + (f"{loan_amount}$" if loan_amount else ("-" if lang == "en" else "ندارد")), TEXT_COLOR),
        ("🏢", ("مدیر بانک: " if lang == "fa" else "Manager: ") + manager_name, TITLE_COLOR),
    ]

    y = 62
    for emoji, text, color in rows:
        draw.rounded_rectangle([20, y, W - 20, y + 38], radius=8, fill=BOX_FILL)
        draw.text((32, y + 8), f"{emoji}  {text}", fill=color, font=font)
        y += 46

    # Footer
    footer = "بانک هر روز ۲٪ سود به حسابت اضافه میکنه!" if lang == "fa" else "Bank adds 2% daily interest to your account!"
    fb = draw.textbbox((0, 0), footer, font=font_sm)
    draw.text(((W - fb[2] + fb[0]) // 2, H - 22), footer, fill=(150, 150, 170), font=font_sm)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf


# ── Manager selection ──────────────────────────────────────
def _ensure_manager(data: dict, cid: str) -> dict:
    """Return current manager, rotating every 24 h from seen members."""
    mgr = _get_manager(data, cid)
    now = _now()
    if mgr:
        try:
            set_at = datetime.fromisoformat(mgr.get("set_at", ""))
            if (now - set_at).total_seconds() < MANAGER_DURATION:
                return mgr
        except ValueError:
            pass
    # Pick a new manager from seen members
    members = data.get("seen_members", {}).get(cid, [])
    if not members:
        return {}
    chosen_id = random.choice(members)
    names = data.get("user_names", {}).get(cid, {})
    chosen_name = names.get(str(chosen_id), f"User {chosen_id}")
    new_mgr = {
        "user_id": chosen_id,
        "name": chosen_name,
        "set_at": now.isoformat(),
        "embezzled": False,
    }
    _set_manager(data, cid, new_mgr)
    return new_mgr


# ════════════════════════════════════════════════════════════
# 1. /bank
# ════════════════════════════════════════════════════════════
async def bank_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user
    lang = get_lang(chat.id)
    _remember_user(chat.id, user)

    cid, uid = str(chat.id), str(user.id)
    args = context.args or []

    # ── deposit ─────────────────────────────────────────
    if args and args[0].lower() in ("deposit", "واریز"):
        if len(args) < 2 or not args[1].isdigit():
            msg = "📥 مثال: `/bank deposit 500`" if lang == "fa" else "📥 Usage: `/bank deposit 500`"
            await update.message.reply_text(msg, parse_mode="Markdown")
            return

        amount = int(args[1])
        if amount <= 0:
            return

        wallet = get_balance(chat.id, user.id)
        if amount > wallet:
            msg = (f"❌ موجودی کیف پول کافی نیست! ({wallet}$)"
                   if lang == "fa"
                   else f"❌ Not enough wallet balance! ({wallet}$)")
            await update.message.reply_text(msg, parse_mode="Markdown")
            return

        data = load_data()
        acc = _get_bank_account(data, cid, uid) or {"balance": 0, "last_interest": _now().isoformat()}
        _apply_interest(acc)
        acc["balance"] = acc.get("balance", 0) + amount
        _set_bank_account(data, cid, uid, acc)

        # Manager bonus
        mgr = _ensure_manager(data, cid)
        bonus = 0
        if mgr and str(mgr.get("user_id", "")) != uid:
            bonus = int(amount * MANAGER_BONUS_RATE)
            mgr_uid = str(mgr["user_id"])
            mgr_acc = _get_bank_account(data, cid, mgr_uid) or {"balance": 0, "last_interest": _now().isoformat()}
            mgr_acc["balance"] = mgr_acc.get("balance", 0) + bonus
            _set_bank_account(data, cid, mgr_uid, mgr_acc)

        save_data(data)
        add_balance(chat.id, user.id, -amount)

        if lang == "fa":
            msg = f"✅ *{amount}$* به حساب بانکی واریز شد.\n🏦 موجودی بانک: *{acc['balance']}$*\n💰 کیف پول: *{get_balance(chat.id, user.id)}$*"
            if bonus:
                msg += f"\n💼 مدیر بانک ({mgr.get('name', '?')}) *{bonus}$* پاداش گرفت."
        else:
            msg = f"✅ Deposited *{amount}$* to your bank account.\n🏦 Bank balance: *{acc['balance']}$*\n💰 Wallet: *{get_balance(chat.id, user.id)}$*"
            if bonus:
                msg += f"\n💼 Bank manager ({mgr.get('name', '?')}) earned *{bonus}$* bonus."
        await update.message.reply_text(msg, parse_mode="Markdown")
        return

    # ── withdraw ────────────────────────────────────────
    if args and args[0].lower() in ("withdraw", "برداشت"):
        if len(args) < 2 or not args[1].isdigit():
            msg = "📤 مثال: `/bank withdraw 500`" if lang == "fa" else "📤 Usage: `/bank withdraw 500`"
            await update.message.reply_text(msg, parse_mode="Markdown")
            return

        amount = int(args[1])
        if amount <= 0:
            return

        data = load_data()
        acc = _get_bank_account(data, cid, uid)
        if not acc:
            acc = {"balance": 0, "last_interest": _now().isoformat()}
        _apply_interest(acc)

        if amount > acc.get("balance", 0):
            msg = (f"❌ موجودی بانک کافی نیست! ({acc.get('balance', 0)}$)"
                   if lang == "fa"
                   else f"❌ Not enough bank balance! ({acc.get('balance', 0)}$)")
            await update.message.reply_text(msg, parse_mode="Markdown")
            return

        acc["balance"] -= amount
        _set_bank_account(data, cid, uid, acc)
        save_data(data)
        add_balance(chat.id, user.id, amount)

        if lang == "fa":
            msg = f"✅ *{amount}$* از حساب بانکی برداشت شد.\n🏦 موجودی بانک: *{acc['balance']}$*\n💰 کیف پول: *{get_balance(chat.id, user.id)}$*"
        else:
            msg = f"✅ Withdrew *{amount}$* from your bank account.\n🏦 Bank balance: *{acc['balance']}$*\n💰 Wallet: *{get_balance(chat.id, user.id)}$*"
        await update.message.reply_text(msg, parse_mode="Markdown")
        return

    # ── status (default) ───────────────────────────────
    data = load_data()
    acc = _get_bank_account(data, cid, uid) or {"balance": 0, "last_interest": _now().isoformat()}
    _apply_interest(acc)
    _set_bank_account(data, cid, uid, acc)

    loan = _get_loan(data, cid, uid)
    loan_amt = loan.get("amount", 0) if loan else 0

    mgr = _ensure_manager(data, cid)
    save_data(data)

    wallet_bal = get_balance(chat.id, user.id)
    bank_bal = acc.get("balance", 0)
    mgr_name = mgr.get("name", ("-" if lang == "en" else "نامشخص")) if mgr else ("-" if lang == "en" else "نامشخص")
    interest_str = f"{INTEREST_RATE * 100:.0f}%"

    buf = _render_bank_card(lang, (user.full_name or user.first_name or "User"),
                            wallet_bal, bank_bal, interest_str, loan_amt, mgr_name)

    if lang == "fa":
        caption = (
            f"🏦 *حساب بانکی {user.first_name}*\n\n"
            f"💰 کیف پول: *{wallet_bal}$*\n"
            f"🏦 موجودی بانک: *{bank_bal}$*\n"
            f"📈 نرخ سود روزانه: *{interest_str}*\n"
            f"📋 وام: *{loan_amt}$*\n"
            f"🏢 مدیر بانک: *{mgr_name}*\n\n"
            f"📥 واریز: `/bank deposit [مبلغ]`\n"
            f"📤 برداشت: `/bank withdraw [مبلغ]`"
        )
    else:
        caption = (
            f"🏦 *{user.first_name}'s Bank Account*\n\n"
            f"💰 Wallet: *{wallet_bal}$*\n"
            f"🏦 Bank Balance: *{bank_bal}$*\n"
            f"📈 Daily Interest: *{interest_str}*\n"
            f"📋 Loan: *{loan_amt}$*\n"
            f"🏢 Manager: *{mgr_name}*\n\n"
            f"📥 Deposit: `/bank deposit [amount]`\n"
            f"📤 Withdraw: `/bank withdraw [amount]`"
        )
    await update.message.reply_photo(photo=buf, caption=caption, parse_mode="Markdown")


# ════════════════════════════════════════════════════════════
# 2. /loan
# ════════════════════════════════════════════════════════════
async def loan_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user
    lang = get_lang(chat.id)
    _remember_user(chat.id, user)

    cid, uid = str(chat.id), str(user.id)
    args = context.args or []
    sub = args[0].lower() if args else "status"

    # ── take ────────────────────────────────────────────
    if sub in ("take", "گرفتن"):
        if len(args) < 2 or not args[1].isdigit():
            msg = "📝 مثال: `/loan take 1000`" if lang == "fa" else "📝 Usage: `/loan take 1000`"
            await update.message.reply_text(msg, parse_mode="Markdown")
            return

        amount = int(args[1])
        if amount <= 0:
            return

        data = load_data()
        existing = _get_loan(data, cid, uid)
        if existing and existing.get("amount", 0) > 0:
            msg = ("❌ شما قبلاً وام فعال دارید! اول وامتان را پس بدهید."
                   if lang == "fa"
                   else "❌ You already have an active loan! Pay it off first.")
            await update.message.reply_text(msg, parse_mode="Markdown")
            return

        if amount > LOAN_MAX:
            msg = (f"❌ حداکثر وام *{LOAN_MAX}$* است."
                   if lang == "fa"
                   else f"❌ Maximum loan is *{LOAN_MAX}$*.")
            await update.message.reply_text(msg, parse_mode="Markdown")
            return

        total_due = int(amount * (1 + LOAN_INTEREST))
        _set_loan(data, cid, uid, {
            "amount": total_due,
            "original": amount,
            "taken_at": _now().isoformat(),
            "interest": LOAN_INTEREST,
        })
        save_data(data)
        add_balance(chat.id, user.id, amount)

        if lang == "fa":
            msg = (f"✅ وام *{amount}$* دریافت شد.\n"
                   f"💸 بازپرداخت: *{total_due}$* (سود {int(LOAN_INTEREST*100)}%)\n"
                   f"⏰ اگر تا ۲۴ ساعت پس ندهید، {int(LOAN_PENALTY_RATE*100)}% جریمه اضافه میشود!\n"
                   f"💰 کیف پول: *{get_balance(chat.id, user.id)}$*")
        else:
            msg = (f"✅ Loan of *{amount}$* granted.\n"
                   f"💸 Repayment: *{total_due}$* ({int(LOAN_INTEREST*100)}% interest)\n"
                   f"⏰ If not repaid in 24h, {int(LOAN_PENALTY_RATE*100)}% penalty will be added!\n"
                   f"💰 Wallet: *{get_balance(chat.id, user.id)}$*")
        await update.message.reply_text(msg, parse_mode="Markdown")
        return

    # ── pay ─────────────────────────────────────────────
    if sub in ("pay", "پرداخت"):
        if len(args) < 2 or not args[1].isdigit():
            msg = "📝 مثال: `/loan pay 500`" if lang == "fa" else "📝 Usage: `/loan pay 500`"
            await update.message.reply_text(msg, parse_mode="Markdown")
            return

        amount = int(args[1])
        if amount <= 0:
            return

        data = load_data()
        loan = _get_loan(data, cid, uid)
        if not loan or loan.get("amount", 0) <= 0:
            msg = "✅ شما وام فعالی ندارید!" if lang == "fa" else "✅ You have no active loan!"
            await update.message.reply_text(msg, parse_mode="Markdown")
            return

        # Apply late penalty
        _apply_loan_penalty(loan)

        wallet = get_balance(chat.id, user.id)
        if amount > wallet:
            msg = (f"❌ موجودی کافی نیست! ({wallet}$)"
                   if lang == "fa"
                   else f"❌ Not enough balance! ({wallet}$)")
            await update.message.reply_text(msg, parse_mode="Markdown")
            return

        pay_amount = min(amount, loan["amount"])
        loan["amount"] -= pay_amount
        add_balance(chat.id, user.id, -pay_amount)

        if loan["amount"] <= 0:
            _del_loan(data, cid, uid)
            save_data(data)
            if lang == "fa":
                msg = f"🎉 وام شما کاملاً پرداخت شد!\n💰 کیف پول: *{get_balance(chat.id, user.id)}$*"
            else:
                msg = f"🎉 Your loan is fully paid off!\n💰 Wallet: *{get_balance(chat.id, user.id)}$*"
        else:
            _set_loan(data, cid, uid, loan)
            save_data(data)
            if lang == "fa":
                msg = f"✅ *{pay_amount}$* پرداخت شد.\n📋 باقی‌مانده وام: *{loan['amount']}$*\n💰 کیف پول: *{get_balance(chat.id, user.id)}$*"
            else:
                msg = f"✅ Paid *{pay_amount}$*.\n📋 Remaining loan: *{loan['amount']}$*\n💰 Wallet: *{get_balance(chat.id, user.id)}$*"
        await update.message.reply_text(msg, parse_mode="Markdown")
        return

    # ── status (default) ───────────────────────────────
    data = load_data()
    loan = _get_loan(data, cid, uid)
    if not loan or loan.get("amount", 0) <= 0:
        msg = "✅ شما وام فعالی ندارید." if lang == "fa" else "✅ You have no active loan."
        await update.message.reply_text(msg, parse_mode="Markdown")
        return

    _apply_loan_penalty(loan)
    _set_loan(data, cid, uid, loan)
    save_data(data)

    taken_str = loan.get("taken_at", "?")
    if lang == "fa":
        msg = (f"📋 *وضعیت وام*\n\n"
               f"💸 بدهی فعلی: *{loan['amount']}$*\n"
               f"💵 مبلغ اولیه: *{loan.get('original', '?')}$*\n"
               f"📈 نرخ سود: *{int(LOAN_INTEREST*100)}%*\n"
               f"🕐 زمان دریافت: `{taken_str}`\n\n"
               f"📝 پرداخت: `/loan pay [مبلغ]`")
    else:
        msg = (f"📋 *Loan Status*\n\n"
               f"💸 Current debt: *{loan['amount']}$*\n"
               f"💵 Original: *{loan.get('original', '?')}$*\n"
               f"📈 Interest: *{int(LOAN_INTEREST*100)}%*\n"
               f"🕐 Taken at: `{taken_str}`\n\n"
               f"📝 Pay: `/loan pay [amount]`")
    await update.message.reply_text(msg, parse_mode="Markdown")


# ════════════════════════════════════════════════════════════
# 6. /bankrob — Collaborative bank robbery (4+ people)
# ════════════════════════════════════════════════════════════
BANKROB_MIN_PEOPLE = 4
BANKROB_COOLDOWN = 1800          # 30 min between attempts per chat
BANKROB_JAIL_DURATION = 14400    # 4 hours jail on failure
BANKROB_BASE_LOOT = 800          # base loot per person on success
BANKROB_BONUS_PER_EXTRA = 150   # extra loot per person beyond 4

async def bankrob_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user
    lang = get_lang(chat.id)
    _remember_user(chat.id, user)

    cid = str(chat.id)
    uid = str(user.id)

    # Jail check
    remaining = _check_jail(chat.id, user.id)
    if remaining is not None:
        mins = remaining // 60
        secs = remaining % 60
        msg = (f"⛓️ تو زندانی! ({mins}m {secs}s باقی‌مانده)"
               if lang == "fa"
               else f"⛓️ You're in jail! ({mins}m {secs}s remaining)")
        await update.message.reply_text(msg, parse_mode="Markdown")
        return

    data = load_data()
    rob_data = data.setdefault("bank_robbery", {}).setdefault(cid, {
        "members": [], "last_attempt": ""
    })

    now = _now()

    # Check cooldown
    if rob_data.get("last_attempt"):
        try:
            last_dt = datetime.fromisoformat(rob_data["last_attempt"])
            elapsed = (now - last_dt).total_seconds()
            if elapsed < BANKROB_COOLDOWN:
                cd_left = int(BANKROB_COOLDOWN - elapsed)
                mins = cd_left // 60
                secs = cd_left % 60
                msg = (f"⏳ باید *{mins} دقیقه و {secs} ثانیه* صبر کنید!"
                       if lang == "fa"
                       else f"⏳ Wait *{mins}m {secs}s* before next robbery!")
                await update.message.reply_text(msg, parse_mode="Markdown")
                return
        except ValueError:
            pass

    # Add user to members
    members = rob_data.get("members", [])
    if user.id not in members:
        members.append(user.id)
    rob_data["members"] = members
    data["bank_robbery"][cid] = rob_data
    save_data(data)

    u_name = user.first_name or "User"
    count = len(members)

    if count < BANKROB_MIN_PEOPLE:
        needed = BANKROB_MIN_PEOPLE - count
        if lang == "fa":
            msg = (f"🏦💣 *{u_name}* وارد تیم سرقت شد!\n\n"
                   f"👥 اعضای تیم: *{count}/{BANKROB_MIN_PEOPLE}*\n"
                   f"⏳ هنوز *{needed}* نفر دیگه لازمه!\n"
                   f"بقیه هم /bankrob بزنن تا عملیات شروع شه!")
        else:
            msg = (f"🏦💣 *{u_name}* joined the heist crew!\n\n"
                   f"👥 Crew: *{count}/{BANKROB_MIN_PEOPLE}*\n"
                   f"⏳ Need *{needed}* more people!\n"
                   f"Others use /bankrob to join!")
        await update.message.reply_text(msg, parse_mode="Markdown")
        return

    # Enough people — execute the heist!
    # Markov AI acts as police — smarter AI = harder robbery
    from handlers.markov_ai import get_brain_stats
    brain_keys, _ = get_brain_stats()

    # Success chance: starts at 45%, decreases as AI gets smarter
    # Every 500 bigram keys reduces chance by 2% (AI learns patterns)
    ai_penalty = min(0.20, (brain_keys / 500) * 0.02)
    extra_people = max(0, count - BANKROB_MIN_PEOPLE)
    success_chance = min(0.70, 0.45 - ai_penalty + extra_people * 0.05)
    success_chance = max(0.15, success_chance)

    # Reset robbery data
    rob_data["members"] = []
    rob_data["last_attempt"] = now.isoformat()
    data["bank_robbery"][cid] = rob_data
    save_data(data)

    police_report = _police_report(lang)

    if random.random() < success_chance:
        # SUCCESS!
        loot_per_person = BANKROB_BASE_LOOT + extra_people * BANKROB_BONUS_PER_EXTRA
        total_loot = loot_per_person * count

        for mid in members:
            add_balance(chat.id, mid, loot_per_person)

        if lang == "fa":
            msg = (f"🏦💰 *سرقت موفقیت‌آمیز بود!*\n\n"
                   f"👥 {count} نفر بانک رو زدن!\n"
                   f"💵 هر نفر *{loot_per_person}$* سهم برد!\n"
                   f"💰 کل غنیمت: *{total_loot}$*\n"
                   f"🤫 فعلاً کسی نفهمید...\n"
                   f"📊 شانس موفقیت: *{int(success_chance * 100)}%*")
        else:
            msg = (f"🏦💰 *Bank Heist SUCCESSFUL!*\n\n"
                   f"👥 {count} people pulled off the heist!\n"
                   f"💵 Each got *{loot_per_person}$*!\n"
                   f"💰 Total loot: *{total_loot}$*\n"
                   f"🤫 Nobody noticed... yet.\n"
                   f"📊 Success chance was: *{int(success_chance * 100)}%*")
    else:
        # FAILURE! Everyone goes to jail
        for mid in members:
            set_jail_time(chat.id, mid,
                          f"{now.isoformat()}|{BANKROB_JAIL_DURATION}")

        if lang == "fa":
            msg = (f"🚨🏦 *سرقت ناموفق!*\n\n"
                   f"📄 گزارش پلیس:\n_{police_report}_\n\n"
                   f"👮 پلیس هوش مصنوعی همه رو دستگیر کرد!\n"
                   f"⛓️ همه {count} نفر *{BANKROB_JAIL_DURATION // 3600} ساعت* زندان!\n"
                   f"🧠 هوش پلیس: *{brain_keys}* الگو\n"
                   f"📊 شانس موفقیت: *{int(success_chance * 100)}%* بود")
        else:
            msg = (f"🚨🏦 *Bank Heist FAILED!*\n\n"
                   f"📄 Police report:\n_{police_report}_\n\n"
                   f"👮 AI Police caught everyone!\n"
                   f"⛓️ All {count} members jailed for *{BANKROB_JAIL_DURATION // 3600} hours*!\n"
                   f"🧠 Police AI: *{brain_keys}* patterns learned\n"
                   f"📊 Success chance was: *{int(success_chance * 100)}%*")

    await update.message.reply_text(msg, parse_mode="Markdown")


def _apply_loan_penalty(loan: dict):
    """Add 20% penalty if > 24 h overdue (once)."""
    if loan.get("penalised"):
        return
    taken_str = loan.get("taken_at", "")
    if not taken_str:
        return
    try:
        taken_dt = datetime.fromisoformat(taken_str)
    except ValueError:
        return
    if (_now() - taken_dt).total_seconds() > LOAN_PENALTY_HOURS * 3600:
        loan["amount"] = int(loan["amount"] * (1 + LOAN_PENALTY_RATE))
        loan["penalised"] = True


# ════════════════════════════════════════════════════════════
# 3. /bankmanager
# ════════════════════════════════════════════════════════════
async def bankmanager_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    lang = get_lang(chat.id)
    _remember_user(chat.id, update.effective_user)

    cid = str(chat.id)
    data = load_data()
    mgr = _ensure_manager(data, cid)
    save_data(data)

    if not mgr:
        msg = ("❌ هنوز مدیر بانکی انتخاب نشده. کاربران باید اول فعال باشند!"
               if lang == "fa"
               else "❌ No bank manager yet. Users need to be active first!")
        await update.message.reply_text(msg, parse_mode="Markdown")
        return

    try:
        set_at = datetime.fromisoformat(mgr.get("set_at", ""))
        expires = set_at + timedelta(seconds=MANAGER_DURATION)
        remaining = max(0, int((expires - _now()).total_seconds()))
        hours = remaining // 3600
        mins = (remaining % 3600) // 60
        time_str = f"{hours}h {mins}m"
    except ValueError:
        time_str = "?"

    mgr_name = mgr.get("name", "?")
    if lang == "fa":
        msg = (f"🏢 *مدیر بانک فعلی*\n\n"
               f"👤 نام: *{mgr_name}*\n"
               f"⏳ زمان باقی‌مانده: *{time_str}*\n"
               f"💼 مدیر بانک از هر واریز ۵٪ پاداش دریافت می‌کند.")
    else:
        msg = (f"🏢 *Current Bank Manager*\n\n"
               f"👤 Name: *{mgr_name}*\n"
               f"⏳ Time remaining: *{time_str}*\n"
               f"💼 The manager earns 5% bonus on all deposits.")
    await update.message.reply_text(msg, parse_mode="Markdown")


# ════════════════════════════════════════════════════════════
# 4. /embezzle
# ════════════════════════════════════════════════════════════
async def embezzle_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user
    lang = get_lang(chat.id)
    _remember_user(chat.id, user)

    cid, uid = str(chat.id), str(user.id)

    # Jail check
    remaining = _check_jail(chat.id, user.id)
    if remaining is not None:
        mins = remaining // 60
        secs = remaining % 60
        msg = (f"⛓️ تو هنوز زندانی! ({mins}m {secs}s باقی‌مانده)"
               if lang == "fa"
               else f"⛓️ You're still in jail! ({mins}m {secs}s remaining)")
        await update.message.reply_text(msg, parse_mode="Markdown")
        return

    data = load_data()
    mgr = _ensure_manager(data, cid)

    if not mgr or mgr.get("user_id") != user.id:
        msg = ("❌ فقط مدیر بانک می‌تواند اختلاس کند!"
               if lang == "fa"
               else "❌ Only the bank manager can embezzle!")
        await update.message.reply_text(msg, parse_mode="Markdown")
        save_data(data)
        return

    if random.random() < EMBEZZLE_SUCCESS_CHANCE:
        # Success
        add_balance(chat.id, user.id, EMBEZZLE_AMOUNT)
        mgr["embezzled"] = True
        _set_manager(data, cid, mgr)
        save_data(data)

        if lang == "fa":
            msg = (f"💰 اختلاس موفق! *{EMBEZZLE_AMOUNT}$* از خزانه بانک دزدیدی!\n"
                   f"🤫 امیدوارم کسی نفهمه...\n"
                   f"💰 کیف پول: *{get_balance(chat.id, user.id)}$*")
        else:
            msg = (f"💰 Embezzlement successful! You stole *{EMBEZZLE_AMOUNT}$* from the bank reserve!\n"
                   f"🤫 Hope nobody finds out...\n"
                   f"💰 Wallet: *{get_balance(chat.id, user.id)}$*")
    else:
        # Caught
        report = _police_report(lang)

        # Lose bank balance
        acc = _get_bank_account(data, cid, uid)
        lost_bank = 0
        if acc and acc.get("balance", 0) > 0:
            lost_bank = acc["balance"]
            acc["balance"] = 0
            _set_bank_account(data, cid, uid, acc)

        # Lose all stocks
        stocks = get_stocks(chat.id, user.id)
        lost_stocks = bool(stocks)
        if stocks:
            set_stocks(chat.id, user.id, {})

        save_data(data)

        # Jail for 6 hours
        set_jail_time(chat.id, user.id,
                      f"{_now().isoformat()}|{JAIL_DURATION_EMBEZZLE}")

        if lang == "fa":
            msg = (f"🚨 *اختلاس ناموفق! دستگیر شدی!*\n\n"
                   f"📄 گزارش پلیس:\n_{report}_\n\n"
                   f"⛓️ زندان: *۶ ساعت*\n"
                   f"🏦 موجودی بانک از دست رفته: *{lost_bank}$*\n")
            if lost_stocks:
                msg += "📉 تمام سهام از دست رفت!\n"
            msg += f"💰 کیف پول: *{get_balance(chat.id, user.id)}$*"
        else:
            msg = (f"🚨 *Embezzlement failed! You got caught!*\n\n"
                   f"📄 Police report:\n_{report}_\n\n"
                   f"⛓️ Jail: *6 hours*\n"
                   f"🏦 Bank balance lost: *{lost_bank}$*\n")
            if lost_stocks:
                msg += "📉 All stocks lost!\n"
            msg += f"💰 Wallet: *{get_balance(chat.id, user.id)}$*"

    await update.message.reply_text(msg, parse_mode="Markdown")


# ════════════════════════════════════════════════════════════
# 5. /investigate
# ════════════════════════════════════════════════════════════
async def investigate_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user
    lang = get_lang(chat.id)
    _remember_user(chat.id, user)

    cid, uid = str(chat.id), str(user.id)

    # Jail check
    remaining = _check_jail(chat.id, user.id)
    if remaining is not None:
        mins = remaining // 60
        secs = remaining % 60
        msg = (f"⛓️ تو هنوز زندانی! ({mins}m {secs}s باقی‌مانده)"
               if lang == "fa"
               else f"⛓️ You're still in jail! ({mins}m {secs}s remaining)")
        await update.message.reply_text(msg, parse_mode="Markdown")
        return

    wallet = get_balance(chat.id, user.id)
    if wallet < INVESTIGATE_COST:
        msg = (f"❌ بررسی هزینه *{INVESTIGATE_COST}$* دارد. موجودی شما: *{wallet}$*"
               if lang == "fa"
               else f"❌ Investigation costs *{INVESTIGATE_COST}$*. Your balance: *{wallet}$*")
        await update.message.reply_text(msg, parse_mode="Markdown")
        return

    data = load_data()
    mgr = _ensure_manager(data, cid)
    save_data(data)

    if not mgr:
        msg = ("❌ مدیر بانکی وجود ندارد!"
               if lang == "fa"
               else "❌ No bank manager exists!")
        await update.message.reply_text(msg, parse_mode="Markdown")
        return

    mgr_id = mgr.get("user_id")
    mgr_name = mgr.get("name", "?")

    if mgr_id == user.id:
        msg = ("❌ نمی‌توانید خودتان را بازرسی کنید!"
               if lang == "fa"
               else "❌ You can't investigate yourself!")
        await update.message.reply_text(msg, parse_mode="Markdown")
        return

    # Deduct cost
    add_balance(chat.id, user.id, -INVESTIGATE_COST)

    found_evidence = random.random() < INVESTIGATE_SUCCESS_CHANCE
    embezzled = mgr.get("embezzled", False)

    if found_evidence and embezzled:
        # Manager goes to jail
        set_jail_time(chat.id, mgr_id,
                      f"{_now().isoformat()}|{JAIL_DURATION_EMBEZZLE}")
        # Lose manager's bank balance
        data = load_data()
        mgr_uid = str(mgr_id)
        mgr_acc = _get_bank_account(data, cid, mgr_uid)
        lost = 0
        if mgr_acc and mgr_acc.get("balance", 0) > 0:
            lost = mgr_acc["balance"]
            mgr_acc["balance"] = 0
            _set_bank_account(data, cid, mgr_uid, mgr_acc)
        # Reset embezzled flag
        mgr["embezzled"] = False
        _set_manager(data, cid, mgr)
        save_data(data)

        report = _police_report(lang)
        reward = INVESTIGATE_COST * 2
        add_balance(chat.id, user.id, reward)

        if lang == "fa":
            msg = (f"🔍 *بازرسی موفق!*\n\n"
                   f"📄 گزارش:\n_{report}_\n\n"
                   f"🚨 مدیر بانک *{mgr_name}* به جرم اختلاس دستگیر شد!\n"
                   f"⛓️ ۶ ساعت زندان!\n"
                   f"🏦 موجودی بانک مدیر ({lost}$) مصادره شد.\n"
                   f"🎁 پاداش بازرسی: *{reward}$*\n"
                   f"💰 کیف پول: *{get_balance(chat.id, user.id)}$*")
        else:
            msg = (f"🔍 *Investigation successful!*\n\n"
                   f"📄 Report:\n_{report}_\n\n"
                   f"🚨 Bank manager *{mgr_name}* arrested for embezzlement!\n"
                   f"⛓️ 6 hours in jail!\n"
                   f"🏦 Manager's bank balance ({lost}$) confiscated.\n"
                   f"🎁 Investigation reward: *{reward}$*\n"
                   f"💰 Wallet: *{get_balance(chat.id, user.id)}$*")
    elif found_evidence and not embezzled:
        if lang == "fa":
            msg = (f"🔍 بازرسی انجام شد.\n"
                   f"✅ مدیر بانک *{mgr_name}* پاک است! مدرکی یافت نشد.\n"
                   f"💸 هزینه: *{INVESTIGATE_COST}$*\n"
                   f"💰 کیف پول: *{get_balance(chat.id, user.id)}$*")
        else:
            msg = (f"🔍 Investigation complete.\n"
                   f"✅ Manager *{mgr_name}* is clean! No evidence found.\n"
                   f"💸 Cost: *{INVESTIGATE_COST}$*\n"
                   f"💰 Wallet: *{get_balance(chat.id, user.id)}$*")
    else:
        if lang == "fa":
            msg = (f"🔍 بازرسی انجام شد ولی مدرکی پیدا نشد.\n"
                   f"💸 هزینه: *{INVESTIGATE_COST}$*\n"
                   f"💰 کیف پول: *{get_balance(chat.id, user.id)}$*")
        else:
            msg = (f"🔍 Investigation done but no evidence found.\n"
                   f"💸 Cost: *{INVESTIGATE_COST}$*\n"
                   f"💰 Wallet: *{get_balance(chat.id, user.id)}$*")

    await update.message.reply_text(msg, parse_mode="Markdown")
