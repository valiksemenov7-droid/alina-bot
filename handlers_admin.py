import asyncio
import csv
import io

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError, TelegramRetryAfter
from aiogram.filters import BaseFilter, Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import BufferedInputFile, CallbackQuery, Message

import db
from strings import LANG_NAMES
from ui import esc, kb, loc, plain, show

router = Router()


class IsAdmin(BaseFilter):
    async def __call__(self, event) -> bool:
        return bool(event.from_user) and db.is_admin(event.from_user.id)


router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())


class A(StatesGroup):
    when = State()
    msg = State()
    svc = State()
    svc_new = State()
    text = State()
    media = State()
    cast = State()
    admin_id = State()


STATUS_LABEL = {"new": "🆕 Новые", "in_progress": "🔄 В обработке", "confirmed": "✅ Подтверждены",
                "rescheduled": "🔁 Перенесены", "cancelled": "❌ Отменены"}
STATUS_ONE = {"new": "🆕 новая", "in_progress": "🔄 в обработке", "confirmed": "✅ подтверждена",
              "rescheduled": "🔁 перенесена", "cancelled": "❌ отменена"}
SINGLE_TEXTS = {"privacy_url"}
FIELD_LABEL = {
    "price": "цену (например: 150–250 €)", "old_price": "старую цену (для «вместо …»)",
    "name_ru": "название (RU)", "name_es": "название (ES)", "name_en": "название (EN)",
    "desc_ru": "описание (RU)", "desc_es": "описание (ES)", "desc_en": "описание (EN)",
    "note_ru": "примечание к цене (RU), напр. «за 1 мл»", "note_es": "примечание к цене (ES)",
    "note_en": "примечание к цене (EN)", "admin_note": "внутреннюю заметку (клиенты её не видят)",
}
PAGE = 8
_tasks = set()
_drafts = {}  # broadcast drafts between preview and confirmation (FSM state is cleared by the callback router)


# ------------------------------------------------------------------ bookings: cards & notifications
def card_text(b):
    when = f"\n✅ Подтверждено на: {esc(b['confirmed_at'])}" if b["confirmed_at"] else ""
    return (f"📋 <b>Заявка #{b['id']}</b> — {STATUS_ONE.get(b['status'], b['status'])}\n"
            f"👤 <a href=\"tg://user?id={b['user_id']}\">{esc(b['name'])}</a>\n"
            f"📞 {esc(b['phone'])}\n💆 {esc(b['service'])}\n🗓 Желает: {esc(b['wanted'])}\n"
            f"🌐 {(b['lang'] or '').upper()}\n💬 {esc(b['comment']) or '—'}{when}\n"
            f"🕓 {b['created_at']} UTC")


def card_kb(b):
    i = b["id"]
    return kb([("🔄 В обработку", f"adm:bs:{i}:in_progress"), ("✅ Подтвердить", f"adm:bs:{i}:confirmed")],
              [("🔁 Перенести", f"adm:bs:{i}:rescheduled"), ("❌ Отменить", f"adm:bs:{i}:cancelled")],
              [("✉️ Написать клиенту", f"adm:bm:{i}")],
              [("⬅️ К списку", f"adm:bl:{b['status']}:0"), ("⚙️ Панель", "adm:home")])


async def notify_new_booking(bot, bid):
    b = db.get_booking(bid)
    if not b:
        return
    for aid in db.admin_ids():
        try:
            await bot.send_message(aid, "🔔 <b>Новая заявка!</b>\n\n" + card_text(b), reply_markup=card_kb(b))
        except Exception:
            pass


async def notify_client(bot, b):
    """Send the studio's decision to the client. Returns True if delivered."""
    key = {"confirmed": "n_confirmed", "rescheduled": "n_rescheduled", "cancelled": "n_cancelled"}.get(b["status"])
    if not key:
        return True
    lang = b["lang"] or "ru"
    service = b["service"]
    if b["service_id"]:
        s = db.get_service(b["service_id"])
        if s:
            service = loc(s, "name", lang)
    msg = (db.get_text(key, lang)
           .replace("{service}", esc(service))
           .replace("{when}", esc(b["confirmed_at"]))
           .replace("{address}", db.get_text("address", lang)))
    if b["status"] == "confirmed":
        prep = db.get_text("booking_prep", lang)
        if prep:
            msg += "\n\n" + prep
    try:
        await bot.send_message(b["user_id"], msg)
        return True
    except (TelegramForbiddenError, TelegramBadRequest):
        return False


# ------------------------------------------------------------------ panel
def panel_kb(uid):
    n = db.count_bookings("new")
    rows = [
        [("📋 Заявки" + (f" ({n})" if n else ""), "adm:b")],
        [("💶 Услуги и цены", "adm:s"), ("✏️ Тексты", "adm:t")],
        [("🖼 Портфолио и отзывы", "adm:m")],
        [("👥 Подписчики", "adm:u"), ("📣 Рассылка", "adm:cast")],
    ]
    if db.is_owner(uid):
        rows.append([("🛡 Администраторы", "adm:a")])
    rows.append([("🏠 Меню клиента", "home")])
    return kb(*rows)


PANEL_TEXT = "⚙️ <b>Админ-панель</b>\nЧто настроим?"


@router.message(Command("admin"))
async def cmd_admin(m: Message, state: FSMContext):
    await state.clear()
    await m.answer(PANEL_TEXT, reply_markup=panel_kb(m.from_user.id))


@router.message(Command("cancel"), StateFilter(A))
async def cmd_cancel(m: Message, state: FSMContext):
    await state.clear()
    await m.answer("Отменено.", reply_markup=panel_kb(m.from_user.id))


@router.message(StateFilter(A), F.text.startswith("/"))
async def cmd_in_state(m: Message, state: FSMContext):
    await state.clear()
    await m.answer("Ввод отменён. Повторите команду.")


# ------------------------------------------------------------------ card builders (services / texts)
def svc_card(s):
    cat = db.get_cat(s["cat_id"])
    price = esc(s["price"]) or "—"
    if s["price_from"]:
        price = "от " + price
    if s["old_price"]:
        price += f" (вместо {esc(s['old_price'])})"
    status = ("✅ цена подтверждена — клиенты видят её" if s["confirmed"] and s["price"]
              else "⚠️ цена НЕ подтверждена — клиенты видят «уточните у администратора»")
    descs = " / ".join(f"{l.upper()}: {'есть' if s['desc_' + l] else '—'}" for l in ("ru", "es", "en"))
    review = ("⚠️ описание помечено «требует проверки» — клиентам НЕ показывается" if s["needs_review"]
              else "✅ описание одобрено — показывается клиентам")
    lines = [f"💆 <b>{esc(s['name_ru'])}</b>  <i>({esc(cat['name_ru']) if cat else ''})</i>",
             f"ES: {esc(s['name_es']) or '—'}\nEN: {esc(s['name_en']) or '—'}", "",
             f"💶 {price}", status]
    notes = [esc(s[f"note_{l}"]) for l in ("ru", "es", "en") if s[f"note_{l}"]]
    if notes:
        lines.append("📎 Примечание: " + " | ".join(notes))
    if s["admin_note"]:
        lines.append(f"📝 Заметка: {esc(s['admin_note'])}")
    lines += ["", f"📄 Описание — {descs}", review, "👁 Виден клиентам: " + ("да" if s["active"] else "нет (скрыт)")]
    return "\n".join(lines)


def svc_kb(s):
    i = s["id"]
    return kb(
        [("💶 Цена", f"adm:se:{i}:price"), ("✅ Подтв. цену" if not s["confirmed"] else "⚠️ Снять подтв.", f"adm:se:{i}:conf")],
        [(("«от»: вкл" if s["price_from"] else "«от»: выкл"), f"adm:se:{i}:from"), ("Старая цена", f"adm:se:{i}:old_price")],
        [("Название RU", f"adm:se:{i}:name_ru"), ("ES", f"adm:se:{i}:name_es"), ("EN", f"adm:se:{i}:name_en")],
        [("Описание RU", f"adm:se:{i}:desc_ru"), ("ES", f"adm:se:{i}:desc_es"), ("EN", f"adm:se:{i}:desc_en")],
        [("Примеч. RU", f"adm:se:{i}:note_ru"), ("ES", f"adm:se:{i}:note_es"), ("EN", f"adm:se:{i}:note_en")],
        [("✅ Одобрить описание" if s["needs_review"] else "⚠️ Описание: на проверку", f"adm:se:{i}:rev")],
        [("🙈 Скрыть" if s["active"] else "👁 Показать", f"adm:se:{i}:act"), ("📝 Заметка", f"adm:se:{i}:admin_note")],
        [("🗑 Удалить", f"adm:sdel:{i}")],
        [("⬅️ К списку", f"adm:sc:{s['cat_id']}")])


def text_card(r):
    single = r["key"] in SINGLE_TEXTS
    lines = [f"✏️ <b>{esc(r['label'])}</b>", ""]
    for l in (("ru",) if single else ("ru", "es", "en")):
        lines.append(f"<b>{l.upper()}:</b> {plain(r[l])}")
    lines.append("")
    lines.append("⚠️ Помечен «требует проверки» — клиентам НЕ показывается" if r["needs_review"] else "✅ Показывается клиентам")
    return "\n".join(lines)


def text_kb(r):
    k = r["key"]
    if k in SINGLE_TEXTS:
        edit = [("✏️ Изменить", f"adm:te:{k}:ru")]
    else:
        edit = [("✏️ RU", f"adm:te:{k}:ru"), ("✏️ ES", f"adm:te:{k}:es"), ("✏️ EN", f"adm:te:{k}:en")]
    return kb(edit,
              [("✅ Снять пометку" if r["needs_review"] else "⚠️ Пометить «требует проверки»", f"adm:tr:{k}")],
              [("⬅️ К списку", "adm:t:0")])


def admins_view(owner_id):
    lines = ["🛡 <b>Администраторы</b>", "", f"👑 Владелец: {esc(db.user_name(owner_id))} (<code>{owner_id}</code>)"]
    rows = []
    for a in db.list_admins():
        if a["user_id"] == owner_id:
            continue
        name = a["name"] or db.user_name(a["user_id"])
        lines.append(f"• {esc(name)} (<code>{a['user_id']}</code>)")
        rows.append([(f"🗑 {name[:30]}", f"adm:ad:{a['user_id']}")])
    if not rows:
        lines.append("\nДополнительных администраторов нет.")
    rows = [[("➕ Пригласить по ссылке", "adm:ai")], [("➕ Добавить по Telegram ID", "adm:aid")]] + rows + [[("⬅️ Назад", "adm:home")]]
    return "\n".join(lines), kb(*rows)


# ------------------------------------------------------------------ main callback router
@router.callback_query(F.data.startswith("adm:"))
async def adm_cb(cb: CallbackQuery, state: FSMContext):
    uid = cb.from_user.id
    parts = cb.data.split(":")[1:]
    sec, a = parts[0], parts[1:]

    # pre-checks that need an alert instead of a normal answer
    if sec in ("a", "ai", "aid", "ad", "ad2") and not db.is_owner(uid):
        await cb.answer("Только владелец может управлять администраторами", show_alert=True)
        return
    if sec == "se" and len(a) > 1 and a[1] == "conf":
        s = db.get_service(int(a[0]))
        if s and not s["confirmed"] and not s["price"]:
            await cb.answer("Сначала укажите цену", show_alert=True)
            return
    await cb.answer()
    await state.clear()

    # ---- home
    if sec == "home":
        await show(cb, PANEL_TEXT, panel_kb(uid))

    # ---- bookings
    elif sec == "b":
        rows = [[(f"{STATUS_LABEL[s]} ({db.count_bookings(s)})", f"adm:bl:{s}:0")] for s in db.STATUSES]
        rows.append([("⬅️ Назад", "adm:home")])
        await show(cb, "📋 <b>Заявки</b>", kb(*rows))

    elif sec == "bl":
        status, page = a[0], int(a[1])
        items = db.list_bookings(status, page * PAGE, PAGE)
        total = db.count_bookings(status)
        rows = [[(f"#{b['id']} {b['name'][:18]} · {b['service'][:22]}", f"adm:bv:{b['id']}")] for b in items]
        nav = []
        if page > 0:
            nav.append(("◀️", f"adm:bl:{status}:{page - 1}"))
        if (page + 1) * PAGE < total:
            nav.append(("▶️", f"adm:bl:{status}:{page + 1}"))
        if nav:
            rows.append(nav)
        rows.append([("⬅️ Назад", "adm:b")])
        await show(cb, f"{STATUS_LABEL[status]} — {total}" + ("" if items else "\n\nПусто."), kb(*rows))

    elif sec == "bv":
        b = db.get_booking(int(a[0]))
        if b:
            await show(cb, card_text(b), card_kb(b))

    elif sec == "bs":
        bid, status = int(a[0]), a[1]
        b = db.get_booking(bid)
        if not b or status not in db.STATUSES:
            return
        if status in ("confirmed", "rescheduled"):
            await state.set_state(A.when)
            await state.update_data(bid=bid, status=status)
            await show(cb, f"🗓 Заявка #{bid}: введите дату и время для клиента (например: «15 ноября, 11:00»).\n\n/cancel — отмена",
                       kb([("✖️ Отмена", f"adm:bv:{bid}")]))
            return
        db.set_booking(bid, status)
        b = db.get_booking(bid)
        note = ""
        if status == "cancelled":
            note = "\n\n📨 Клиент уведомлён." if await notify_client(cb.bot, b) else "\n\n⚠️ Не удалось уведомить клиента (бот заблокирован)."
        await show(cb, card_text(b) + note, card_kb(b))

    elif sec == "bm":
        bid = int(a[0])
        await state.set_state(A.msg)
        await state.update_data(bid=bid)
        await show(cb, f"✉️ Заявка #{bid}: отправьте сообщение для клиента — оно придёт от имени бота.\n\n/cancel — отмена",
                   kb([("✖️ Отмена", f"adm:bv:{bid}")]))

    # ---- services & prices
    elif sec == "s":
        rows = [[(c["name_ru"], f"adm:sc:{c['id']}")] for c in db.categories()]
        rows.append([("⬅️ Назад", "adm:home")])
        await show(cb, "💶 <b>Услуги и цены</b>\nВыберите раздел:", kb(*rows))

    elif sec == "sc":
        c = db.get_cat(int(a[0]))
        if not c:
            return
        items = db.services(c["id"], active_only=False)
        rows = []
        for s in items:
            mark = "🙈" if not s["active"] else ("✅" if s["confirmed"] and s["price"] else "⚠️")
            price = s["price"] or "—"
            rows.append([(f"{mark} {s['name_ru'][:34]} · {price[:14]}", f"adm:sv:{s['id']}")])
        rows.append([("➕ Добавить услугу", f"adm:sa:{c['id']}")])
        rows.append([("⬅️ Назад", "adm:s")])
        await show(cb, f"<b>{esc(c['name_ru'])}</b>\n✅ цена подтверждена · ⚠️ не подтверждена · 🙈 скрыта", kb(*rows))

    elif sec == "sv":
        s = db.get_service(int(a[0]))
        if s:
            await show(cb, svc_card(s), svc_kb(s))

    elif sec == "se":
        sid, field = int(a[0]), a[1]
        s = db.get_service(sid)
        if not s:
            return
        if field == "conf":
            db.set_service(sid, "confirmed", 0 if s["confirmed"] else 1)
        elif field == "from":
            db.set_service(sid, "price_from", 0 if s["price_from"] else 1)
        elif field == "rev":
            db.set_service(sid, "needs_review", 0 if s["needs_review"] else 1)
        elif field == "act":
            db.set_service(sid, "active", 0 if s["active"] else 1)
        elif field in FIELD_LABEL:
            await state.set_state(A.svc)
            await state.update_data(sid=sid, field=field)
            hint = "«-» — очистить." + (" Цена станет подтверждённой." if field == "price" else "")
            await show(cb, f"Введите {FIELD_LABEL[field]}.\n{hint}\n\n/cancel — отмена", kb([("✖️ Отмена", f"adm:sv:{sid}")]))
            return
        else:
            return
        s = db.get_service(sid)
        await show(cb, svc_card(s), svc_kb(s))

    elif sec == "sa":
        await state.set_state(A.svc_new)
        await state.update_data(cat=int(a[0]))
        await show(cb, "Введите название новой услуги (RU). Переводы и цену добавите после.\n\n/cancel — отмена",
                   kb([("✖️ Отмена", f"adm:sc:{a[0]}")]))

    elif sec == "sdel":
        s = db.get_service(int(a[0]))
        if s:
            await show(cb, f"Удалить услугу «{esc(s['name_ru'])}»? Это необратимо. Если нужно просто убрать её у клиентов — лучше «Скрыть».",
                       kb([("🗑 Да, удалить", f"adm:sdel2:{s['id']}")], [("⬅️ Нет", f"adm:sv:{s['id']}")]))

    elif sec == "sdel2":
        s = db.get_service(int(a[0]))
        if s:
            db.del_service(s["id"])
            await cb.bot.send_message(uid, "🗑 Услуга удалена.", reply_markup=kb([("⬅️ К списку", f"adm:sc:{s['cat_id']}")]))
            try:
                await cb.bot.delete_message(uid, cb.message.message_id)
            except Exception:
                pass

    # ---- texts
    elif sec == "t":
        page = int(a[0]) if a else 0
        rows_all = db.all_texts()
        chunk_ = rows_all[page * 10:(page + 1) * 10]
        rows = [[(("⚠️ " if r["needs_review"] else "") + r["label"][:50], f"adm:tv:{r['key']}")] for r in chunk_]
        nav = []
        if page > 0:
            nav.append(("◀️", f"adm:t:{page - 1}"))
        if (page + 1) * 10 < len(rows_all):
            nav.append(("▶️", f"adm:t:{page + 1}"))
        if nav:
            rows.append(nav)
        rows.append([("⬅️ Назад", "adm:home")])
        await show(cb, "✏️ <b>Тексты бота</b>\nВыберите, что изменить:", kb(*rows))

    elif sec == "tv":
        r = db.text_row(a[0])
        if r:
            await show(cb, text_card(r), text_kb(r))

    elif sec == "tr":
        db.toggle_text_review(a[0])
        r = db.text_row(a[0])
        await show(cb, text_card(r), text_kb(r))

    elif sec == "te":
        key, lang = a[0], a[1]
        await state.set_state(A.text)
        await state.update_data(key=key, lang=lang)
        r = db.text_row(key)
        extra = "\nМожно использовать форматирование Telegram (жирный, курсив, ссылки)." if key not in SINGLE_TEXTS else ""
        if key.startswith("n_"):
            extra += "\nПодстановки: {service}, {when}, {address}"
        await show(cb, f"Отправьте новый текст: <b>{esc(r['label'])}</b> ({lang.upper()}).{extra}\n«-» — очистить.\n\n/cancel — отмена",
                   kb([("✖️ Отмена", f"adm:tv:{key}")]))

    # ---- portfolio / reviews
    elif sec == "m":
        rows = [[(f"📸 Портфолио ({db.count_media('portfolio')})", "adm:ml:portfolio")],
                [(f"⭐ Отзывы ({db.count_media('review')})", "adm:ml:review")],
                [("⬅️ Назад", "adm:home")]]
        await show(cb, "🖼 <b>Портфолио и отзывы</b>\nКлиенты видят последние 10 фото в каждом разделе.", kb(*rows))

    elif sec == "ml":
        kind = a[0]
        items = db.list_media(kind, 20)
        rows = [[("➕ Добавить фото", f"adm:ma:{kind}")]]
        for i in items:
            rows.append([(f"🗑 #{i['id']} {i['caption'][:28] or 'без подписи'}", f"adm:md:{i['id']}:{kind}")])
        rows.append([("⬅️ Назад", "adm:m")])
        title = "Портфолио" if kind == "portfolio" else "Отзывы"
        await show(cb, f"<b>{title}</b> — всего {db.count_media(kind)}. Нажмите на фото в списке, чтобы удалить его.", kb(*rows))

    elif sec == "ma":
        kind = a[0]
        await state.set_state(A.media)
        await state.update_data(kind=kind)
        await show(cb, "Отправьте одно или несколько фото (можно с подписью). Когда закончите — нажмите «Готово».",
                   kb([("✅ Готово", f"adm:ml:{kind}")]))

    elif sec == "md":
        db.del_media(int(a[0]))
        items = db.list_media(a[1], 20)
        rows = [[("➕ Добавить фото", f"adm:ma:{a[1]}")]]
        for i in items:
            rows.append([(f"🗑 #{i['id']} {i['caption'][:28] or 'без подписи'}", f"adm:md:{i['id']}:{a[1]}")])
        rows.append([("⬅️ Назад", "adm:m")])
        await show(cb, "🗑 Удалено.", kb(*rows))

    # ---- subscribers
    elif sec == "u":
        st = db.user_stats()
        langs = ", ".join(f"{k.upper()}: {v}" for k, v in st["langs"].items())
        text = (f"👥 <b>Подписчики бота</b>\n\nВсего: <b>{st['total']}</b>\nАктивных: {st['active']}\n"
                f"Заблокировали бота / ушли: {st['left']}\nНовых за 24 часа: {st['day']}\nНовых за 7 дней: {st['week']}\n"
                f"Языки (активные): {langs or '—'}")
        await show(cb, text, kb([("📄 Список", "adm:ul:0")], [("📥 Экспорт CSV", "adm:ux")], [("⬅️ Назад", "adm:home")]))

    elif sec == "ul":
        page = int(a[0])
        total = db.user_stats()["total"]
        users = db.list_users(page * 10, 10)
        lines = [f"👥 Подписчики — страница {page + 1}", ""]
        for n, u in enumerate(users, page * 10 + 1):
            uname = f" @{u['username']}" if u["username"] else ""
            lines.append(f"{n}. {esc(u['first_name'])}{esc(uname)} · {(u['lang'] or '—').upper()} · {u['joined_at'][:10]}"
                         + ("" if u["active"] else " · 🚫"))
        nav = []
        if page > 0:
            nav.append(("◀️", f"adm:ul:{page - 1}"))
        if (page + 1) * 10 < total:
            nav.append(("▶️", f"adm:ul:{page + 1}"))
        rows = ([nav] if nav else []) + [[("⬅️ Назад", "adm:u")]]
        await show(cb, "\n".join(lines) + "\n\n🚫 — заблокировал(а) бота", kb(*rows))

    elif sec == "ux":
        buf = io.StringIO()
        w = csv.writer(buf)
        w.writerow(["id", "username", "first_name", "language", "joined_at_utc", "active"])
        for u in db.all_users():
            w.writerow([u["id"], u["username"], u["first_name"], u["lang"], u["joined_at"], u["active"]])
        data = BufferedInputFile(buf.getvalue().encode("utf-8-sig"), filename="subscribers.csv")
        await cb.bot.send_document(uid, data, caption="📥 Подписчики бота")

    # ---- broadcast
    elif sec == "cast":
        rows = [[(f"👥 Все ({db.count_audience('all')})", "adm:casta:all")]]
        rows += [[(f"{LANG_NAMES[l]} ({db.count_audience(l)})", f"adm:casta:{l}")] for l in ("ru", "es", "en")]
        rows.append([("⬅️ Назад", "adm:home")])
        await show(cb, "📣 <b>Рассылка</b>\nКому отправить? (только активные подписчики)", kb(*rows))

    elif sec == "casta":
        aud = a[0]
        await state.set_state(A.cast)
        await state.update_data(aud=aud)
        await show(cb, f"Получателей: <b>{db.count_audience(aud)}</b>.\n\nОтправьте текст рассылки или фото с подписью "
                       f"(подпись до 1024 символов). Форматирование Telegram сохранится.\n\n/cancel — отмена",
                   kb([("✖️ Отмена", "adm:cast")]))

    elif sec == "castgo":
        draft = _drafts.pop(uid, None)
        if not draft:
            await show(cb, "Черновик не найден. Начните заново.", kb([("📣 Рассылка", "adm:cast")]))
            return
        ids = db.audience(draft["aud"])
        await show(cb, f"🚀 Рассылка запущена: {len(ids)} получателей. Пришлю отчёт, когда закончу.", kb([("⚙️ Панель", "adm:home")]))
        task = asyncio.create_task(run_cast(cb.bot, uid, draft["aud"], ids, draft["payload"]))
        _tasks.add(task)
        task.add_done_callback(_tasks.discard)

    elif sec == "castx":
        _drafts.pop(uid, None)
        await show(cb, "Рассылка отменена.", panel_kb(uid))

    # ---- admins (owner only, checked above)
    elif sec == "a":
        text, markup = admins_view(uid)
        await show(cb, text, markup)

    elif sec == "ai":
        token = db.new_invite(uid)
        me = await cb.bot.get_me()
        link = f"https://t.me/{me.username}?start=adm_{token}"
        await show(cb, "🔗 <b>Ссылка-приглашение</b> (одноразовая):\n\n" + link +
                   "\n\nОтправьте её человеку. Когда он откроет ссылку в Telegram и нажмёт «Start», он станет администратором.",
                   kb([("⬅️ Назад", "adm:a")]))

    elif sec == "aid":
        await state.set_state(A.admin_id)
        await show(cb, "Отправьте числовой Telegram ID человека или перешлите сюда любое его сообщение.\n"
                       "ID можно узнать командой /id в этом боте. Чтобы получать уведомления о заявках, человек должен хотя бы раз нажать Start в боте.\n\n/cancel — отмена",
                   kb([("✖️ Отмена", "adm:a")]))

    elif sec == "ad":
        target = int(a[0])
        await show(cb, f"Убрать администратора {esc(db.user_name(target))} (<code>{target}</code>)?",
                   kb([("🗑 Да, убрать", f"adm:ad2:{target}")], [("⬅️ Нет", "adm:a")]))

    elif sec == "ad2":
        target = int(a[0])
        if db.is_owner(target):
            return
        db.remove_admin(target)
        text, markup = admins_view(uid)
        await show(cb, "✅ Администратор удалён.\n\n" + text, markup)


# ------------------------------------------------------------------ FSM inputs
@router.message(A.when, F.text)
async def in_when(m: Message, state: FSMContext):
    d = await state.get_data()
    await state.clear()
    db.set_booking(d["bid"], d["status"], confirmed_at=m.text.strip()[:120])
    b = db.get_booking(d["bid"])
    ok = await notify_client(m.bot, b)
    note = "📨 Клиент уведомлён." if ok else "⚠️ Не удалось уведомить клиента (бот заблокирован)."
    await m.answer(card_text(b) + "\n\n" + note, reply_markup=card_kb(b))


@router.message(A.msg, F.text)
async def in_msg(m: Message, state: FSMContext):
    d = await state.get_data()
    await state.clear()
    b = db.get_booking(d["bid"])
    try:
        await m.bot.send_message(b["user_id"], "✉️ <b>ALINA BEAUTY</b>\n\n" + m.html_text)
        note = "📨 Сообщение отправлено клиенту."
    except (TelegramForbiddenError, TelegramBadRequest):
        note = "⚠️ Не удалось отправить (клиент заблокировал бота)."
    await m.answer(note, reply_markup=card_kb(b))


@router.message(A.svc, F.text)
async def in_svc(m: Message, state: FSMContext):
    d = await state.get_data()
    field = d["field"]
    value = m.html_text.strip() if field.startswith("desc_") else m.text.strip()
    if value == "-":
        value = ""
    if field == "name_ru" and not value:
        await m.answer("Название (RU) не может быть пустым. Введите название или /cancel.")
        return
    await state.clear()
    db.set_service(d["sid"], field, value)
    if field == "price":
        db.set_service(d["sid"], "confirmed", 1 if value else 0)
    s = db.get_service(d["sid"])
    await m.answer("✅ Сохранено.\n\n" + svc_card(s), reply_markup=svc_kb(s))


@router.message(A.svc_new, F.text)
async def in_svc_new(m: Message, state: FSMContext):
    d = await state.get_data()
    await state.clear()
    sid = db.add_service(d["cat"], m.text.strip()[:120])
    s = db.get_service(sid)
    await m.answer("✅ Услуга добавлена (пока без цены — клиенты увидят «уточните у администратора»).\n\n" + svc_card(s),
                   reply_markup=svc_kb(s))


@router.message(A.text, F.text)
async def in_text(m: Message, state: FSMContext):
    d = await state.get_data()
    await state.clear()
    value = m.html_text.strip()
    if value == "-":
        value = ""
    if d["key"] in SINGLE_TEXTS:
        db.set_text_all(d["key"], m.text.strip() if value else "")
    else:
        db.set_text(d["key"], d["lang"], value)
    r = db.text_row(d["key"])
    await m.answer("✅ Сохранено.\n\n" + text_card(r), reply_markup=text_kb(r))


@router.message(A.media, F.photo)
async def in_media(m: Message, state: FSMContext):
    d = await state.get_data()
    mid = db.add_media(d["kind"], m.photo[-1].file_id, (m.caption or "")[:200])
    await m.answer(f"✅ Добавлено (#{mid}). Отправьте ещё или нажмите «Готово».",
                   reply_markup=kb([("✅ Готово", f"adm:ml:{d['kind']}")]))


@router.message(A.media)
async def in_media_wrong(m: Message):
    await m.answer("Пришлите фото (как изображение, не файлом) или нажмите «Готово» выше.")


@router.message(A.cast, F.text | F.photo)
async def cast_input(m: Message, state: FSMContext):
    d = await state.get_data()
    photo = m.photo[-1].file_id if m.photo else None
    text = m.html_text if (m.text or m.caption) else ""
    if photo and len(m.caption or "") > 1024:
        await m.answer("Подпись к фото длиннее 1024 символов. Сократите её или отправьте текстом отдельно.")
        return
    if not photo and not text.strip():
        return
    payload = {"photo": photo, "text": text}
    aud = d["aud"]
    await state.clear()
    _drafts[m.from_user.id] = {"aud": aud, "payload": payload}
    await m.answer("👀 Так увидят подписчики:")
    if photo:
        await m.bot.send_photo(m.chat.id, photo, caption=text or None)
    else:
        await m.answer(text)
    n = db.count_audience(aud)
    await m.answer(f"Отправить <b>{n}</b> получателям?",
                   reply_markup=kb([("🚀 Отправить", "adm:castgo")], [("✖️ Отмена", "adm:castx")]))


@router.message(A.admin_id)
async def in_admin_id(m: Message, state: FSMContext):
    target, name = None, ""
    origin = getattr(m, "forward_origin", None)
    if origin is not None and getattr(origin, "type", "") == "user":
        target, name = origin.sender_user.id, origin.sender_user.full_name
    elif m.text and m.text.strip().lstrip("-").isdigit():
        target = int(m.text.strip())
    if not target:
        await m.answer("Не получилось определить ID. Отправьте число (например 123456789) или перешлите сообщение человека "
                       "(если у него скрыт профиль пересылки — используйте ссылку-приглашение). /cancel — отмена")
        return
    await state.clear()
    if db.is_admin(target):
        await m.answer("Этот человек уже администратор.")
    else:
        db.add_admin(target, name or db.user_name(target), m.from_user.id)
        try:
            await m.bot.send_message(target, "✅ Вас добавили администратором бота ALINA BEAUTY. Откройте панель командой /admin")
            await m.answer("✅ Администратор добавлен и уведомлён.")
        except Exception:
            await m.answer("✅ Администратор добавлен. Но он ещё не запускал бота — пусть нажмёт Start, чтобы получать уведомления.")
    text, markup = admins_view(m.from_user.id)
    await m.answer(text, reply_markup=markup)


# ------------------------------------------------------------------ broadcast worker
async def send_one(bot, uid, p):
    for _ in range(3):
        try:
            if p["photo"]:
                await bot.send_photo(uid, p["photo"], caption=p["text"] or None)
            else:
                await bot.send_message(uid, p["text"])
            return True
        except TelegramRetryAfter as e:
            await asyncio.sleep(e.retry_after + 1)
        except TelegramForbiddenError:
            db.deactivate(uid)
            return False
        except Exception:
            return False
    return False


async def run_cast(bot, admin_id, aud, ids, payload):
    sent = failed = 0
    for uid in ids:
        if await send_one(bot, uid, payload):
            sent += 1
        else:
            failed += 1
        await asyncio.sleep(0.05)  # ~20 msg/s, below Telegram's limit
    db.log_broadcast(admin_id, aud, sent, failed)
    try:
        await bot.send_message(admin_id, f"✅ <b>Рассылка завершена</b>\nДоставлено: {sent}\nНе доставлено: {failed}",
                               reply_markup=kb([("⚙️ Панель", "adm:home")]))
    except Exception:
        pass
