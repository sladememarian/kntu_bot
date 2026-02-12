# ==========================================
# KNTU Bot 25 — Family Tree (Image-based)
# ==========================================

import io
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler
from PIL import Image, ImageDraw, ImageFont

from storage import get_lang, load_data, save_data
from strings import STRINGS

RELATIONS = {
    "fa": {
        "parent": "پدر/مادر 👨‍👩‍👧",
        "child": "فرزند 👶",
        "sibling": "خواهر/برادر 👫",
        "partner": "همسر 💍",
    },
    "en": {
        "parent": "Parent 👨‍👩‍👧",
        "child": "Child 👶",
        "sibling": "Sibling 👫",
        "partner": "Partner 💍",
    },
}

REVERSE = {"parent": "child", "child": "parent", "sibling": "sibling", "partner": "partner"}

# ---------- Image style constants ----------
BG_COLOR = (30, 30, 46)
BOX_FILL = (69, 71, 90)
BOX_BORDER = (137, 180, 250)
ROOT_BORDER = (243, 139, 168)
TEXT_COLOR = (205, 214, 244)
TITLE_COLOR = (137, 180, 250)

LINE_COLORS = {
    "partner": (249, 226, 175),
    "child":   (166, 227, 161),
    "parent":  (203, 166, 247),
    "sibling": (148, 226, 213),
}

BOX_W, BOX_H = 150, 46
H_GAP, V_GAP = 36, 80


def _get_font(size: int) -> ImageFont.FreeTypeFont:
    for p in ["C:\\Windows\\Fonts\\tahoma.ttf",
              "C:\\Windows\\Fonts\\arial.ttf",
              "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]:
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


# ---------- Data helpers ----------

def _get_family(chat_id: int) -> dict:
    data = load_data()
    return data.get("family_tree", {}).get(str(chat_id), {})


def _set_relation(chat_id: int, user1_id: int, user2_id: int, relation: str):
    data = load_data()
    tree = data.setdefault("family_tree", {}).setdefault(str(chat_id), {})
    user1_rels = tree.setdefault(str(user1_id), [])
    for r in user1_rels:
        if r["user_id"] == user2_id and r["relation"] == relation:
            return
    user1_rels.append({"user_id": user2_id, "relation": relation})
    save_data(data)


def _remove_relation(chat_id: int, user1_id: int, user2_id: int):
    data = load_data()
    tree = data.get("family_tree", {}).get(str(chat_id), {})
    rels = tree.get(str(user1_id), [])
    tree[str(user1_id)] = [r for r in rels if r["user_id"] != user2_id]
    rels2 = tree.get(str(user2_id), [])
    tree[str(user2_id)] = [r for r in rels2 if r["user_id"] != user1_id]
    save_data(data)


async def family_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    lang = get_lang(chat.id)
    s = STRINGS[lang]
    args = context.args if context.args else []

    # --- /family tree ---
    if args and args[0] == "tree":
        user = update.effective_user
        if update.message.reply_to_message:
            user = update.message.reply_to_message.from_user
        await _send_family_tree_image(update, context, chat.id, user, lang)
        return

    # --- ADD relation ---
    if args and args[0] == "add":
        if len(args) < 2:
            await update.message.reply_text(s["family_add_usage"], parse_mode="Markdown")
            return
        relation = args[1].lower()
        valid = ("parent", "child", "sibling", "partner")
        if relation not in valid:
            await update.message.reply_text(s["family_add_usage"], parse_mode="Markdown")
            return
        if not update.message.reply_to_message:
            await update.message.reply_text(s["family_reply_needed"], parse_mode="Markdown")
            return

        me = update.effective_user
        target = update.message.reply_to_message.from_user
        if target.id == me.id:
            return
        if target.is_bot:
            return

        # --- Partner requires approval ---
        if relation == "partner":
            me_name = me.first_name or "User"
            target_name = target.first_name or "User"
            callback_accept = f"fam_accept:{chat.id}:{me.id}:{target.id}"
            callback_reject = f"fam_reject:{chat.id}:{me.id}:{target.id}"

            if lang == "fa":
                text = f"💍 *{me_name}* می‌خواد با *{target_name}* ازدواج کنه!\n\n{target_name}، قبول می‌کنی؟"
                buttons = [
                    [
                        InlineKeyboardButton("✅ بله، قبول!", callback_data=callback_accept),
                        InlineKeyboardButton("❌ نه، رد!", callback_data=callback_reject),
                    ]
                ]
            else:
                text = f"💍 *{me_name}* wants to marry *{target_name}*!\n\n{target_name}, do you accept?"
                buttons = [
                    [
                        InlineKeyboardButton("✅ Yes, I do!", callback_data=callback_accept),
                        InlineKeyboardButton("❌ No way!", callback_data=callback_reject),
                    ]
                ]
            await update.message.reply_text(
                text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(buttons)
            )
            return

        # Non-partner relations: add directly
        _set_relation(chat.id, me.id, target.id, relation)
        _set_relation(chat.id, target.id, me.id, REVERSE[relation])

        rel_label = RELATIONS[lang][relation]
        me_name = me.first_name or "User"
        target_name = target.first_name or "User"
        await update.message.reply_text(
            s["family_added"].format(user1=me_name, user2=target_name, relation=rel_label),
            parse_mode="Markdown",
        )
        return

    # --- REMOVE relation ---
    if args and args[0] == "remove":
        if not update.message.reply_to_message:
            await update.message.reply_text(s["family_reply_needed"], parse_mode="Markdown")
            return
        me = update.effective_user
        target = update.message.reply_to_message.from_user
        _remove_relation(chat.id, me.id, target.id)
        await update.message.reply_text(
            s["family_removed"].format(user=target.first_name or "User"),
            parse_mode="Markdown",
        )
        return

    # --- SHOW family list ---
    user = update.effective_user
    if update.message.reply_to_message:
        user = update.message.reply_to_message.from_user

    tree = _get_family(chat.id)
    rels = tree.get(str(user.id), [])

    if not rels:
        await update.message.reply_text(
            s["family_empty"].format(user=user.first_name or "User"),
            parse_mode="Markdown",
        )
        return

    lines = []
    for r in rels:
        rel_label = RELATIONS[lang].get(r["relation"], r["relation"])
        try:
            member = await context.bot.get_chat_member(chat.id, r["user_id"])
            name = member.user.first_name or "User"
        except Exception:
            name = f"User {r['user_id']}"
        lines.append(f"• {rel_label}: *{name}*")

    header = s["family_header"].format(user=user.first_name or "User")
    await update.message.reply_text(
        header + "\n".join(lines), parse_mode="Markdown"
    )


# ==============================
# Partner approval callback
# ==============================
async def family_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data  # e.g. "fam_accept:chatid:requester:target"

    parts = data.split(":")
    if len(parts) != 4:
        await query.answer()
        return

    action = parts[0]
    chat_id = int(parts[1])
    requester_id = int(parts[2])
    target_id = int(parts[3])
    lang = get_lang(chat_id)

    # Only the target can press the button
    if query.from_user.id != target_id:
        if lang == "fa":
            await query.answer("⛔ فقط طرف مقابل می‌تونه جواب بده!", show_alert=True)
        else:
            await query.answer("⛔ Only the proposed person can answer!", show_alert=True)
        return

    try:
        req_member = await context.bot.get_chat_member(chat_id, requester_id)
        req_name = req_member.user.first_name or "User"
    except Exception:
        req_name = f"User {requester_id}"

    target_name = query.from_user.first_name or "User"

    if action == "fam_accept":
        _set_relation(chat_id, requester_id, target_id, "partner")
        _set_relation(chat_id, target_id, requester_id, "partner")
        if lang == "fa":
            text = f"💍✅ *{target_name}* قبول کرد!\n\n*{req_name}* 💕 *{target_name}* الان زوج هستن! 🎉"
        else:
            text = f"💍✅ *{target_name}* accepted!\n\n*{req_name}* 💕 *{target_name}* are now partners! 🎉"
        await query.edit_message_text(text, parse_mode="Markdown")
    elif action == "fam_reject":
        if lang == "fa":
            text = f"💔 *{target_name}* درخواست *{req_name}* رو رد کرد! 😢"
        else:
            text = f"💔 *{target_name}* rejected *{req_name}*'s proposal! 😢"
        await query.edit_message_text(text, parse_mode="Markdown")

    await query.answer()


# ==============================
# Recursive Image Family Tree
# ==============================

async def _resolve_name(context, chat_id: int, uid: int) -> str:
    try:
        m = await context.bot.get_chat_member(chat_id, uid)
        return m.user.first_name or "User"
    except Exception:
        return f"User {uid}"


async def _collect_graph(context, chat_id: int, root_id: int, tree_data: dict) -> dict:
    """Walk the entire connected family graph from root_id. Returns {uid: {name, rels}}."""
    nodes = {}
    visited = set()

    async def walk(uid):
        if uid in visited:
            return
        visited.add(uid)
        name = await _resolve_name(context, chat_id, uid)
        rels = tree_data.get(str(uid), [])
        nodes[uid] = {"name": name, "rels": rels}
        for r in rels:
            await walk(r["user_id"])

    await walk(root_id)
    return nodes


def _layout(nodes: dict, root_id: int):
    """
    Lay out every node reachable from root_id.
    Returns (positions, edges).
      positions: list of {uid, x, y, name, is_root}
      edges:     list of {u1, u2, rel}
    """
    placed = {}        # uid -> (x, y)
    edge_set = set()
    edges = []

    def add_edge(u1, u2, rel):
        key = (min(u1, u2), max(u1, u2), rel)
        if key not in edge_set:
            edge_set.add(key)
            edges.append({"u1": u1, "u2": u2, "rel": rel})

    root = nodes.get(root_id)
    if not root:
        return [], []

    # Classify root's direct relations
    parents, partners, siblings, children = [], [], [], []
    for r in root["rels"]:
        uid = r["user_id"]
        if r["relation"] == "parent":
            parents.append(uid)
        elif r["relation"] == "partner":
            partners.append(uid)
        elif r["relation"] == "sibling":
            siblings.append(uid)
        elif r["relation"] == "child":
            children.append(uid)

    unit = BOX_W + H_GAP

    # ---- Row 1: siblings (left) + root (center) + partners (right) ----
    row1 = siblings + [root_id] + partners
    start_x = -(len(row1) - 1) * unit // 2
    y1 = 0
    for i, uid in enumerate(row1):
        placed[uid] = (start_x + i * unit, y1)
    for p in partners:
        add_edge(root_id, p, "partner")
    for s in siblings:
        add_edge(root_id, s, "sibling")

    # ---- Row 0: parents ----
    if parents:
        y0 = y1 - V_GAP - BOX_H
        px = -(len(parents) - 1) * unit // 2
        for i, uid in enumerate(parents):
            placed[uid] = (px + i * unit, y0)
            add_edge(uid, root_id, "parent")

    # ---- Row 2+: children (recursive) ----
    already = set(placed)

    def _place_children(parent_id, parent_y):
        p_node = nodes.get(parent_id)
        if not p_node:
            return
        kids = [r["user_id"] for r in p_node["rels"]
                if r["relation"] == "child" and r["user_id"] not in already]
        if not kids:
            return

        # For each child, also find their own partners
        groups = []  # (child_id, [partner_ids])
        for kid in kids:
            already.add(kid)
            k_node = nodes.get(kid, {"name": "?", "rels": []})
            k_partners = [r["user_id"] for r in k_node["rels"]
                          if r["relation"] == "partner" and r["user_id"] not in already]
            for kp in k_partners:
                already.add(kp)
            groups.append((kid, k_partners))

        # Count total slots
        total_slots = sum(1 + len(kp) for _, kp in groups)
        cy = parent_y + V_GAP + BOX_H
        cx = placed[parent_id][0] - (total_slots - 1) * unit // 2

        for kid, k_partners in groups:
            placed[kid] = (cx, cy)
            add_edge(parent_id, kid, "child")
            for kp in k_partners:
                cx += unit
                placed[kp] = (cx, cy)
                add_edge(kid, kp, "partner")
            # Recurse into kid's children
            _place_children(kid, cy)
            cx += unit

    _place_children(root_id, y1)
    # Also check partner's children (in case children are only on partner side)
    for pid in partners:
        _place_children(pid, y1)

    positions = []
    for uid, (x, y) in placed.items():
        n = nodes[uid]["name"] if uid in nodes else f"User {uid}"
        positions.append({"uid": uid, "x": x, "y": y, "name": n, "is_root": uid == root_id})

    return positions, edges


def _render_image(positions: list, edges: list, title: str) -> io.BytesIO | None:
    if not positions:
        return None

    font = _get_font(17)
    font_sm = _get_font(13)
    font_title = _get_font(22)

    # Canvas size
    min_x = min(p["x"] for p in positions) - BOX_W // 2 - 50
    max_x = max(p["x"] for p in positions) + BOX_W // 2 + 50
    min_y = min(p["y"] for p in positions) - BOX_H // 2 - 90
    max_y = max(p["y"] for p in positions) + BOX_H // 2 + 70
    cw = max(max_x - min_x, 400)
    ch = max(max_y - min_y, 300) + 50
    ox, oy = -min_x, -min_y + 55

    img = Image.new("RGB", (cw, ch), BG_COLOR)
    draw = ImageDraw.Draw(img)

    # Title
    tb = draw.textbbox((0, 0), title, font=font_title)
    draw.text(((cw - tb[2] + tb[0]) // 2, 14), title, fill=TITLE_COLOR, font=font_title)

    # Map uid -> pixel center
    ctr = {p["uid"]: (p["x"] + ox, p["y"] + oy) for p in positions}

    # Draw edges
    for e in edges:
        u1, u2, rel = e["u1"], e["u2"], e["rel"]
        if u1 not in ctr or u2 not in ctr:
            continue
        x1, y1 = ctr[u1]
        x2, y2 = ctr[u2]
        clr = LINE_COLORS.get(rel, TEXT_COLOR)

        if rel in ("partner", "sibling"):
            # Horizontal line — direction-aware (left→right)
            w = 3 if rel == "partner" else 2
            if x1 < x2:
                draw.line([(x1 + BOX_W // 2, y1), (x2 - BOX_W // 2, y2)], fill=clr, width=w)
            else:
                draw.line([(x1 - BOX_W // 2, y1), (x2 + BOX_W // 2, y2)], fill=clr, width=w)
            if rel == "partner":
                mx, my = (x1 + x2) // 2, (y1 + y2) // 2
                draw.text((mx - 4, my - 10), "♥", fill=ROOT_BORDER, font=font)
        elif rel in ("child", "parent"):
            # Vertical connector
            mid_y = (y1 + y2) // 2
            draw.line([(x1, y1 + BOX_H // 2), (x1, mid_y)], fill=clr, width=2)
            draw.line([(x1, mid_y), (x2, mid_y)], fill=clr, width=2)
            draw.line([(x2, mid_y), (x2, y2 - BOX_H // 2)], fill=clr, width=2)

    # Draw boxes
    for p in positions:
        cx, cy = ctr[p["uid"]]
        x0, y0 = cx - BOX_W // 2, cy - BOX_H // 2
        x1, y1 = x0 + BOX_W, y0 + BOX_H
        border = ROOT_BORDER if p["is_root"] else BOX_BORDER
        draw.rounded_rectangle([x0, y0, x1, y1], radius=12, fill=BOX_FILL, outline=border, width=3)

        name = p["name"]
        if len(name) > 14:
            name = name[:13] + "…"
        tb = draw.textbbox((0, 0), name, font=font)
        tw, th = tb[2] - tb[0], tb[3] - tb[1]
        draw.text((cx - tw // 2, cy - th // 2), name, fill=TEXT_COLOR, font=font)

    # Legend
    ly = ch - 32
    items = [("♥ Partner", LINE_COLORS["partner"]),
             ("↓ Child", LINE_COLORS["child"]),
             ("↑ Parent", LINE_COLORS["parent"]),
             ("↔ Sibling", LINE_COLORS["sibling"])]
    lx = 12
    for lbl, c in items:
        draw.rectangle([lx, ly, lx + 10, ly + 10], fill=c)
        draw.text((lx + 14, ly - 2), lbl, fill=TEXT_COLOR, font=font_sm)
        lx += 105

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf


async def _send_family_tree_image(update: Update, context, chat_id: int, user, lang: str):
    s = STRINGS[lang]
    tree_data = _get_family(chat_id)
    uname = user.first_name or "User"

    if not tree_data.get(str(user.id)):
        await update.message.reply_text(
            s["family_empty"].format(user=uname), parse_mode="Markdown")
        return

    nodes = await _collect_graph(context, chat_id, user.id, tree_data)
    title = f"{uname}'s Family Tree"
    positions, edges = _layout(nodes, user.id)
    buf = _render_image(positions, edges, title)

    if buf:
        await update.message.reply_photo(photo=buf, caption=f"🌳 {title}")
    else:
        await update.message.reply_text(
            s["family_empty"].format(user=uname), parse_mode="Markdown")
