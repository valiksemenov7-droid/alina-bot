import os
import re

from aiogram import F, Router
from aiogram.filters import Command, CommandObject, CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (CallbackQuery, FSInputFile, InputMediaPhoto, KeyboardButton, Message,
                           ReplyKeyboardMarkup, ReplyKeyboardRemove)

import config
import db
import handlers_admin as adm
from strings import DIV, LANG_NAMES, LANGS, t
from ui import cat_emoji, esc, esc_attr, head, kb, loc, price_html, show, svc_line, visible_desc

router = Router()


class Book(StatesGroup):
    name = State()
    phone = State()
    when = State()
    comment = State()
    lang = State()
    confirm = State()


# ------------------------------------------------------------------ helpers
def lang_kb():
    return kb(*[[(LANG_NAMES[l], f"lang:{l}")] for l in LANGS])


def main_menu(lang, uid):
    rows = [
        [(t("m_book", lang), "book")],
        [(t("m_services", lang), "m:services"), (t("m_price", lang), "m:price")],
        [(t("m_inject", lang), "g:inject")],
        [(t("m_face", lang), "g:face")],
        [(t("m_body", lang), "g:body")],
        [(t("m_promos", lang), "m:promos")],
        [(t("m_portfolio", lang), "m:portfolio"), (t("m_reviews", lang), "m:reviews")],
        [(t("m_faq", lang), "m:faq"), (t("m_contact", lang), "m:contact")],
        [(t("m_lang", lang), "m:lang")],
    ]
    if db.is_admin(uid):
        rows.append([("⚙️ Админ-панель", "adm:home")])
    return kb(*rows)


def privacy_html(lang):
    s = db.get_text("privacy", lang)
    url = db.get_text("privacy_url", "ru").strip()
    if url.startswith("http"):
        s += f'\n<a href="{esc_attr(url)}">{t("privacy_link", lang)}</a>'
    return s


async def send_home(m: Message, uid, lang, first=False):
    text = db.get_text("welcome", lang) or "<b>ALINA BEAUTY ESTHETIC</b>"
    if first:
        text += "\n\n" + privacy_html(lang)
    markup = main_menu(lang, uid)
    if first and os.path.exists(config.LOGO_PATH) and len(text) <= 1000:
        await m.answer_photo(FSInputFile(config.LOGO_PATH), caption=text, reply_markup=markup)
    else:
        await m.answer(text, reply_markup=markup)


def home_row(lang):
    return [(t("home", lang), "home")]


def book_row(lang, data="book"):
    return [(t("m_book", lang), data)]


def catalog_page(cats, lang, back):
    blocks, infos, inject = [], [], False
    for c in cats:
        items = db.services(c["id"])
        if not items:
            continue
        if c["grp"] == "inject":
            inject = True
        lines = [head(cat_emoji(c["id"]), loc(c, "name", lang))]
        for s_ in items:
            lines.append(svc_line(s_, lang))
            if visible_desc(s_, lang):
                infos.append([("📖 " + loc(s_, "name", lang)[:55], f"s:{s_['id']}")])
        blocks.append("\n".join(lines))
    text = "\n\n".join(blocks) or "—"
    if infos:
        text += "\n\n" + t("tap_info", lang)
    disc = db.get_text("disclaimer", lang)
    if disc:
        text += f"\n\n{DIV}\n{disc}"
    if inject:
        safety = db.get_text("safety_inject", lang)
        if safety:
            text += "\n\n" + safety
    rows = infos[:15] + [book_row(lang), [(t("back", lang), back), (t("home", lang), "home")]]
    return text, kb(*rows)


# ------------------------------------------------------------------ /start & commands
@router.message(CommandStart())
async def cmd_start(m: Message, command: CommandObject, state: FSMContext):
    await state.clear()
    u = m.from_user
    db.upsert_user(u)
    arg = (command.args or "").strip()
    if arg.startswith("adm_"):
        if db.use_invite(arg[4:], u.id):
            db.add_admin(u.id, u.full_name, config.OWNER_ID)
            await m.answer("✅ Вы добавлены как администратор бота. Откройте панель командой /admin")
            if config.OWNER_ID:
                try:
                    await m.bot.send_message(config.OWNER_ID, f"✅ {esc(u.full_name)} (<code>{u.id}</code>) принял(а) приглашение и теперь администратор.")
                except Exception:
                    pass
        else:
            await m.answer("Ссылка-приглашение недействительна или уже использована.")
    if not db.has_lang(u.id):
        await m.answer(t("lang_prompt", "ru") + "\n" + t("lang_prompt", "es") + "\n" + t("lang_prompt", "en"),
                       reply_markup=lang_kb())
        return
    await send_home(m, u.id, db.get_lang(u.id))


@router.message(Command("menu"))
async def cmd_menu(m: Message, state: FSMContext):
    await state.clear()
    db.upsert_user(m.from_user)
    if not db.has_lang(m.from_user.id):
        await m.answer(t("lang_prompt", "ru"), reply_markup=lang_kb())
        return
    await send_home(m, m.from_user.id, db.get_lang(m.from_user.id))


@router.message(Command("cancel"))
async def cmd_cancel(m: Message, state: FSMContext):
    # admin-side states are handled by the admin router first; this one covers client flows
    lang = db.get_lang(m.from_user.id)
    if await state.get_state() is not None:
        await state.clear()
        await m.answer(t("b_cancelled", lang), reply_markup=ReplyKeyboardRemove())
    await send_home(m, m.from_user.id, lang)


@router.message(Command("id"))
async def cmd_id(m: Message):
    await m.answer(f"Your Telegram ID: <code>{m.from_user.id}</code>")


# ------------------------------------------------------------------ navigation
@router.callback_query(F.data.startswith(("m:", "g:", "c:", "s:", "f:", "lang:")) | (F.data == "home"))
async def nav(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    uid = cb.from_user.id
    db.upsert_user(cb.from_user)
    lang = db.get_lang(uid)
    kind, _, arg = cb.data.partition(":")
    await cb.answer()

    if kind == "lang":
        if arg not in LANGS:
            return
        had = db.has_lang(uid)
        db.set_lang(uid, arg)
        try:
            await cb.bot.delete_message(uid, cb.message.message_id)
        except Exception:
            pass
        await send_home(cb.message, uid, arg, first=not had)
        return

    if kind == "home":
        await show(cb, db.get_text("welcome", lang) or "<b>ALINA BEAUTY ESTHETIC</b>", main_menu(lang, uid))

    elif kind == "m" and arg == "lang":
        await show(cb, t("lang_prompt", lang), lang_kb())

    elif kind == "m" and arg == "services":
        rows = [[(f"{cat_emoji(c['id'])} {loc(c, 'name', lang)}", f"c:{c['id']}")] for c in db.categories()]
        rows.append(home_row(lang))
        await show(cb, t("pick_section", lang), kb(*rows))

    elif kind == "m" and arg == "price":
        blocks = [f"💰 <b>{t('price_title', lang)}</b>\n<i>ALINA BEAUTY ESTHETIC</i>"]
        for c in db.categories():
            items = db.services(c["id"])
            if not items:
                continue
            blocks.append("\n".join([head(cat_emoji(c["id"]), loc(c, "name", lang))] + [svc_line(x, lang) for x in items]))
        disc = db.get_text("disclaimer", lang)
        if disc:
            blocks.append(f"{DIV}\n{disc}")
        blocks.append(t("tap_book", lang))
        await show(cb, "\n\n".join(blocks), kb(book_row(lang), home_row(lang)))

    elif kind == "g":
        cats = db.categories(arg)
        text, markup = catalog_page(cats, lang, "home")
        await show(cb, text, markup)

    elif kind == "c" and arg.isdigit():
        c = db.get_cat(int(arg))
        if c:
            text, markup = catalog_page([c], lang, "m:services")
            await show(cb, text, markup)

    elif kind == "s" and arg.isdigit():
        s = db.get_service(int(arg))
        if not s:
            return
        c = db.get_cat(s["cat_id"])
        text = head(cat_emoji(s["cat_id"]), loc(s, "name", lang)) + "\n" + price_html(s, lang)
        desc = visible_desc(s, lang)
        text += f"\n\n📖 <b>{t('about', lang)}</b>\n{desc}" if desc else f"\n\n💬 {t('no_desc', lang)}"
        if c and c["grp"] == "inject":
            for key in ("disclaimer", "safety_inject"):
                extra = db.get_text(key, lang)
                if extra:
                    text += "\n\n" + extra
        await show(cb, text, kb(book_row(lang, f"bk:{s['id']}"),
                                [(t("back", lang), f"c:{s['cat_id']}"), (t("home", lang), "home")]))

    elif kind == "m" and arg == "promos":
        await show(cb, db.get_text("promos", lang) or "—", kb(book_row(lang), home_row(lang)))

    elif kind == "m" and arg in ("portfolio", "reviews"):
        mkind = "portfolio" if arg == "portfolio" else "review"
        items = list(reversed(db.list_media(mkind, 10)))
        chat = uid
        try:
            await cb.bot.delete_message(chat, cb.message.message_id)
        except Exception:
            pass
        title = t("m_portfolio" if arg == "portfolio" else "m_reviews", lang)
        if items:
            try:
                if len(items) == 1:
                    await cb.bot.send_photo(chat, items[0]["file_id"], caption=items[0]["caption"] or None)
                else:
                    await cb.bot.send_media_group(chat, [InputMediaPhoto(media=i["file_id"], caption=i["caption"] or None) for i in items])
            except Exception:
                pass
            text = f"<b>{title}</b>\n{DIV}"
        else:
            text = t("no_portfolio" if arg == "portfolio" else "no_reviews", lang)
        await cb.bot.send_message(chat, text, reply_markup=kb([(t("instagram", lang), config.INSTAGRAM_URL)],
                                                              book_row(lang), home_row(lang)))

    elif kind == "m" and arg == "faq":
        rows = []
        for i in range(1, 20):
            q_ = db.get_text(f"faq{i}_q", lang)
            if db.text_row(f"faq{i}_q") is None:
                break
            if q_:
                rows.append([(q_[:60], f"f:{i}")])
        rows.append(home_row(lang))
        await show(cb, t("faq_title", lang), kb(*rows))

    elif kind == "f" and arg.isdigit():
        q_, a_ = db.get_text(f"faq{arg}_q", lang), db.get_text(f"faq{arg}_a", lang)
        await show(cb, f"{head('❓', q_)}\n{a_ or t('no_desc', lang)}",
                   kb([(t("back", lang), "m:faq"), (t("home", lang), "home")], book_row(lang)))

    elif kind == "m" and arg == "contact":
        text = db.get_text("contacts", lang) or "—"
        hours = db.get_text("hours", lang)
        windows = db.get_text("windows", lang)
        if hours:
            text += f"\n\n🕐 <b>{t('hours_lbl', lang)}</b>\n{hours}"
        if windows:
            text += f"\n\n🗓 <b>{t('slots_lbl', lang)}</b>\n{windows}"
        await show(cb, text, kb([(t("instagram", lang), config.INSTAGRAM_URL)], book_row(lang), home_row(lang)))


# ------------------------------------------------------------------ booking flow
def cancel_row(lang):
    return [(t("b_cancel_btn", lang), "bcancel")]


def step(n, lang):
    return f"📅 <b>{t('b_title', lang)}</b> · <i>{t('b_step', lang, n=n, total=6)}</i>\n{DIV}\n"


async def ask_service(cb, lang):
    rows = [[(f"{cat_emoji(c['id'])} {loc(c, 'name', lang)}", f"bc:{c['id']}")] for c in db.categories()]
    rows.append([(t("b_other", lang), "bs:0")])
    rows.append(cancel_row(lang))
    await show(cb, step(1, lang) + t("b_pick_cat", lang), kb(*rows))


async def ask_name(cb, state, lang):
    await state.set_state(Book.name)
    n = cb.from_user.first_name or "—"
    await show(cb, step(2, lang) + t("b_name", lang), kb([(t("b_use_tg", lang, n=n), "bn")], cancel_row(lang)))


async def ask_phone(bot, chat_id, lang):
    markup = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=t("b_phone_btn", lang), request_contact=True)]],
        resize_keyboard=True, one_time_keyboard=True)
    await bot.send_message(chat_id, step(3, lang) + t("b_phone", lang), reply_markup=markup)


def blang_kb(lang):
    rows = [[(LANG_NAMES[l], f"bl:{l}")] for l in LANGS]
    rows.append(cancel_row(lang))
    return kb(*rows)


def summary(d, lang):
    return (f"📋 <b>{t('b_summary_title', lang)}</b>\n{DIV}\n"
            f"👤 <b>{t('lbl_name', lang)}:</b> {esc(d.get('name'))}\n"
            f"📱 <b>{t('lbl_phone', lang)}:</b> {esc(d.get('phone'))}\n"
            f"💆 <b>{t('lbl_service', lang)}:</b> {esc(d.get('service_label') or d.get('service'))}\n"
            f"🗓 <b>{t('lbl_when', lang)}:</b> {esc(d.get('wanted'))}\n"
            f"🌐 <b>{t('lbl_lang', lang)}:</b> {LANG_NAMES.get(d.get('blang'), '—')}\n"
            f"💬 <b>{t('lbl_comment', lang)}:</b> {esc(d.get('comment')) or '—'}")


@router.callback_query(F.data.startswith("bk:") | (F.data == "book"))
async def book_start(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    uid = cb.from_user.id
    db.upsert_user(cb.from_user)
    lang = db.get_lang(uid)
    await cb.answer()
    if cb.data.startswith("bk:"):
        s = db.get_service(int(cb.data[3:]))
        if s:
            await state.update_data(service=s["name_ru"], service_id=s["id"], service_label=loc(s, "name", lang))
    if not db.has_consent(uid):
        await show(cb, privacy_html(lang), kb([(t("b_consent_btn", lang), "bconsent")], cancel_row(lang)))
    elif (await state.get_data()).get("service"):
        await ask_name(cb, state, lang)
    else:
        await ask_service(cb, lang)


@router.callback_query(F.data == "bconsent")
async def b_consent(cb: CallbackQuery, state: FSMContext):
    uid = cb.from_user.id
    lang = db.get_lang(uid)
    db.set_consent(uid)
    await cb.answer()
    if (await state.get_data()).get("service"):
        await ask_name(cb, state, lang)
    else:
        await ask_service(cb, lang)


@router.callback_query(F.data == "bsel")
async def b_sel(cb: CallbackQuery):
    await cb.answer()
    await ask_service(cb, db.get_lang(cb.from_user.id))


@router.callback_query(F.data.startswith("bc:"))
async def b_cat(cb: CallbackQuery):
    lang = db.get_lang(cb.from_user.id)
    await cb.answer()
    rows = [[(loc(s, "name", lang)[:60], f"bs:{s['id']}")] for s in db.services(int(cb.data[3:]))]
    rows.append([(t("back", lang), "bsel")])
    rows.append(cancel_row(lang))
    await show(cb, step(1, lang) + t("b_pick_svc", lang), kb(*rows))


@router.callback_query(F.data.startswith("bs:"))
async def b_svc(cb: CallbackQuery, state: FSMContext):
    lang = db.get_lang(cb.from_user.id)
    await cb.answer()
    sid = int(cb.data[3:])
    s = db.get_service(sid) if sid else None
    if s:
        await state.update_data(service=s["name_ru"], service_id=s["id"], service_label=loc(s, "name", lang))
    else:
        await state.update_data(service="Консультация / другое", service_id=0, service_label=t("b_other", lang))
    await ask_name(cb, state, lang)


@router.callback_query(F.data == "bn", Book.name)
async def b_name_tg(cb: CallbackQuery, state: FSMContext):
    lang = db.get_lang(cb.from_user.id)
    await cb.answer()
    await state.update_data(name=cb.from_user.full_name[:80])
    await state.set_state(Book.phone)
    await ask_phone(cb.bot, cb.from_user.id, lang)


@router.message(Book.name, F.text)
async def b_name(m: Message, state: FSMContext):
    lang = db.get_lang(m.from_user.id)
    name = m.text.strip()
    if not 2 <= len(name) <= 80:
        await m.answer(t("b_name", lang))
        return
    await state.update_data(name=name)
    await state.set_state(Book.phone)
    await ask_phone(m.bot, m.chat.id, lang)


@router.message(Book.phone, F.contact | F.text)
async def b_phone(m: Message, state: FSMContext):
    lang = db.get_lang(m.from_user.id)
    if m.contact:
        phone = m.contact.phone_number
        phone = phone if phone.startswith("+") else "+" + phone
    else:
        phone = m.text.strip()
        if not 7 <= len(re.sub(r"\D", "", phone)) <= 15:
            await m.answer(t("b_phone_bad", lang))
            return
    await state.update_data(phone=phone)
    await state.set_state(Book.when)
    await m.answer(t("b_phone_ok", lang), reply_markup=ReplyKeyboardRemove())
    text = step(4, lang) + t("b_when", lang)
    windows = db.get_text("windows", lang)
    if windows:
        text += f"\n\n🗓 <b>{t('slots_lbl', lang)}</b>\n{windows}"
    await m.answer(text, reply_markup=kb(cancel_row(lang)))


@router.message(Book.when, F.text)
async def b_when(m: Message, state: FSMContext):
    lang = db.get_lang(m.from_user.id)
    await state.update_data(wanted=m.text.strip()[:200])
    await state.set_state(Book.comment)
    await m.answer(step(5, lang) + t("b_comment", lang), reply_markup=kb([(t("b_skip", lang), "bskip")], cancel_row(lang)))


@router.message(Book.comment, F.text)
async def b_comment(m: Message, state: FSMContext):
    lang = db.get_lang(m.from_user.id)
    await state.update_data(comment=m.text.strip()[:500])
    await state.set_state(Book.lang)
    await m.answer(step(6, lang) + t("b_lang", lang), reply_markup=blang_kb(lang))


@router.callback_query(F.data == "bskip", Book.comment)
async def b_skip(cb: CallbackQuery, state: FSMContext):
    lang = db.get_lang(cb.from_user.id)
    await cb.answer()
    await state.update_data(comment="")
    await state.set_state(Book.lang)
    await show(cb, step(6, lang) + t("b_lang", lang), blang_kb(lang))


@router.callback_query(F.data.startswith("bl:"), Book.lang)
async def b_lang(cb: CallbackQuery, state: FSMContext):
    lang = db.get_lang(cb.from_user.id)
    await cb.answer()
    choice = cb.data[3:]
    await state.update_data(blang=choice if choice in LANGS else lang)
    await state.set_state(Book.confirm)
    d = await state.get_data()
    await show(cb, summary(d, lang), kb([(t("b_send", lang), "bsend")], cancel_row(lang)))


@router.callback_query(F.data == "bsend", Book.confirm)
async def b_send(cb: CallbackQuery, state: FSMContext):
    uid = cb.from_user.id
    lang = db.get_lang(uid)
    await cb.answer()
    d = await state.get_data()
    await state.clear()
    if not d.get("name") or not d.get("phone"):
        await show(cb, t("fallback", lang), main_menu(lang, uid))
        return
    bid = db.add_booking(uid, d["name"], d["phone"], d.get("service", "—"), d.get("service_id", 0),
                         d.get("wanted", "—"), d.get("blang", lang), d.get("comment", ""))
    await show(cb, t("b_sent", lang), kb(home_row(lang)))
    await adm.notify_new_booking(cb.bot, bid)


@router.callback_query(F.data == "bcancel")
async def b_cancel(cb: CallbackQuery, state: FSMContext):
    uid = cb.from_user.id
    lang = db.get_lang(uid)
    await cb.answer()
    await state.clear()
    await show(cb, t("b_cancelled", lang), main_menu(lang, uid))


# wrong input types inside the booking flow
@router.message(StateFilter(Book.name, Book.when, Book.comment))
async def b_wrong_type(m: Message):
    await m.answer(t("b_bad_text", db.get_lang(m.from_user.id)))


# ------------------------------------------------------------------ fallback
@router.message(StateFilter(None), F.text)
async def fallback(m: Message):
    uid = m.from_user.id
    db.upsert_user(m.from_user)
    if not db.has_lang(uid):
        await m.answer(t("lang_prompt", "ru"), reply_markup=lang_kb())
        return
    lang = db.get_lang(uid)
    await m.answer(t("fallback", lang), reply_markup=main_menu(lang, uid))
