import html
import re

from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup

from strings import DIV, LANGS, t


def esc(s):
    return html.escape(str(s or ""), quote=False)


def esc_attr(s):
    return html.escape(str(s or ""), quote=True)


def plain(s, limit=350):
    s = re.sub(r"<[^>]+>", "", s or "")
    s = html.unescape(s).strip()
    if len(s) > limit:
        s = s[:limit] + "…"
    return esc(s) if s else "—"


def kb(*rows):
    """kb([("Text", "callback")], [("Link", "https://...")])"""
    out = []
    for row in rows:
        r = []
        for text, data in row:
            if data.startswith("http"):
                r.append(InlineKeyboardButton(text=text, url=data))
            else:
                r.append(InlineKeyboardButton(text=text, callback_data=data))
        out.append(r)
    return InlineKeyboardMarkup(inline_keyboard=out)


def chunk(text, limit=3800):
    if len(text) <= limit:
        return [text]
    parts, cur = [], ""
    for line in text.split("\n"):
        if len(cur) + len(line) + 1 > limit and cur:
            parts.append(cur)
            cur = ""
        cur += line + "\n"
    if cur.strip():
        parts.append(cur)
    return [p.strip("\n") for p in parts]


async def show(cb: CallbackQuery, text, markup=None):
    """Edit the message under a button in place (or replace it if it can't be edited, e.g. a photo)."""
    bot, chat_id, mid = cb.bot, cb.from_user.id, cb.message.message_id
    chunks = chunk(text)
    first, rest = chunks[0], chunks[1:]
    done = False
    try:
        await bot.edit_message_text(first, chat_id=chat_id, message_id=mid,
                                    reply_markup=None if rest else markup)
        done = True
    except TelegramBadRequest as e:
        if "not modified" in str(e).lower():
            done = True
    if not done:
        try:
            await bot.delete_message(chat_id, mid)
        except Exception:
            pass
        await bot.send_message(chat_id, first, reply_markup=None if rest else markup)
    for i, c in enumerate(rest):
        await bot.send_message(chat_id, c, reply_markup=markup if i == len(rest) - 1 else None)


async def reply(event, text, markup=None):
    if isinstance(event, CallbackQuery):
        await show(event, text, markup)
    else:
        for i, c in enumerate(chunk(text)):
            await event.answer(c, reply_markup=markup)


def loc(row, base, lang):
    v = row[f"{base}_{lang}"] if lang in LANGS else ""
    return v or row[f"{base}_ru"]


def price_str(s, lang):
    if not s["confirmed"] or not s["price"]:
        return t("ask_admin", lang)
    p = s["price"]
    if s["price_from"]:
        p = f"{t('from_w', lang)} {p}"
    if s["old_price"]:
        p += f" ({t('instead', lang)} {s['old_price']})"
    note = loc(s, "note", lang)
    if note:
        p += f" · {note}"
    return p


CAT_EMOJI = {1: "✨", 2: "💉", 3: "🧪", 4: "🌿"}


def cat_emoji(cid):
    return CAT_EMOJI.get(cid, "✨")


def head(emoji, title):
    """Section heading: emoji + bold title + thin divider."""
    return f"{emoji} <b>{esc(title)}</b>\n{DIV}"


def price_html(s, lang):
    """💰 price line (with old price struck through and optional note), or 💬 'ask the administrator'."""
    if not s["confirmed"] or not s["price"]:
        return f"💬 <i>{esc(t('ask_admin', lang))}</i>"
    p = esc(s["price"])
    if s["price_from"]:
        p = f"{esc(t('from_w', lang))} {p}"
    out = f"💰 <b>{p}</b>"
    if s["old_price"]:
        out += f"  <s>{esc(s['old_price'])}</s>"
    note = loc(s, "note", lang)
    if note:
        out += f"\n🏷 <i>{esc(note)}</i>"
    return out


def svc_line(s, lang):
    return f"▫️ <b>{esc(loc(s, 'name', lang))}</b>\n{price_html(s, lang)}"


def visible_desc(s, lang):
    """Descriptions flagged 'needs specialist review' are never shown to clients."""
    if s["needs_review"]:
        return ""
    return (loc(s, "desc", lang) or "").strip()
