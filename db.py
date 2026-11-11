import os
import secrets
import sqlite3
from datetime import datetime, timedelta, timezone

import config

_c = None

SCHEMA = """
CREATE TABLE IF NOT EXISTS users(
    id INTEGER PRIMARY KEY, username TEXT DEFAULT '', first_name TEXT DEFAULT '',
    lang TEXT DEFAULT '', joined_at TEXT, active INTEGER DEFAULT 1, consent INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS admins(
    user_id INTEGER PRIMARY KEY, name TEXT DEFAULT '', added_by INTEGER, added_at TEXT);
CREATE TABLE IF NOT EXISTS invites(
    token TEXT PRIMARY KEY, created_by INTEGER, created_at TEXT, used_by INTEGER);
CREATE TABLE IF NOT EXISTS categories(
    id INTEGER PRIMARY KEY, grp TEXT, sort INTEGER, name_ru TEXT, name_es TEXT DEFAULT '', name_en TEXT DEFAULT '');
CREATE TABLE IF NOT EXISTS services(
    id INTEGER PRIMARY KEY AUTOINCREMENT, cat_id INTEGER, sort INTEGER,
    name_ru TEXT, name_es TEXT DEFAULT '', name_en TEXT DEFAULT '',
    price TEXT DEFAULT '', price_from INTEGER DEFAULT 0, old_price TEXT DEFAULT '',
    note_ru TEXT DEFAULT '', note_es TEXT DEFAULT '', note_en TEXT DEFAULT '',
    confirmed INTEGER DEFAULT 0, active INTEGER DEFAULT 1,
    desc_ru TEXT DEFAULT '', desc_es TEXT DEFAULT '', desc_en TEXT DEFAULT '',
    needs_review INTEGER DEFAULT 0, admin_note TEXT DEFAULT '');
CREATE TABLE IF NOT EXISTS texts(
    key TEXT PRIMARY KEY, label TEXT, sort INTEGER DEFAULT 0,
    ru TEXT DEFAULT '', es TEXT DEFAULT '', en TEXT DEFAULT '', needs_review INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS media(
    id INTEGER PRIMARY KEY AUTOINCREMENT, kind TEXT, file_id TEXT, caption TEXT DEFAULT '', added_at TEXT);
CREATE TABLE IF NOT EXISTS bookings(
    id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, name TEXT, phone TEXT,
    service TEXT, service_id INTEGER DEFAULT 0, wanted TEXT, lang TEXT, comment TEXT DEFAULT '',
    status TEXT DEFAULT 'new', confirmed_at TEXT DEFAULT '', created_at TEXT);
CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY, value TEXT);
CREATE TABLE IF NOT EXISTS broadcasts(
    id INTEGER PRIMARY KEY AUTOINCREMENT, admin_id INTEGER, audience TEXT, sent INTEGER, failed INTEGER, created_at TEXT);
"""


def now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def init():
    global _c
    d = os.path.dirname(config.DB_PATH)
    if d:
        os.makedirs(d, exist_ok=True)
    _c = sqlite3.connect(config.DB_PATH, isolation_level=None, check_same_thread=False)
    _c.row_factory = sqlite3.Row
    _c.execute("PRAGMA journal_mode=WAL")
    _c.executescript(SCHEMA)


def q(sql, args=()):
    return _c.execute(sql, args).fetchall()


def one(sql, args=()):
    return _c.execute(sql, args).fetchone()


def run(sql, args=()):
    return _c.execute(sql, args).lastrowid


# ---------------------------------------------------------------- users
def upsert_user(u):
    if one("SELECT 1 FROM users WHERE id=?", (u.id,)):
        run("UPDATE users SET username=?, first_name=?, active=1 WHERE id=?",
            (u.username or "", u.first_name or "", u.id))
    else:
        run("INSERT INTO users(id, username, first_name, lang, joined_at) VALUES(?,?,?,?,?)",
            (u.id, u.username or "", u.first_name or "", "", now()))


def get_lang(uid):
    r = one("SELECT lang FROM users WHERE id=?", (uid,))
    return r["lang"] if r and r["lang"] else "ru"


def has_lang(uid):
    r = one("SELECT lang FROM users WHERE id=?", (uid,))
    return bool(r and r["lang"])


def set_lang(uid, lang):
    run("UPDATE users SET lang=? WHERE id=?", (lang, uid))


def has_consent(uid):
    r = one("SELECT consent FROM users WHERE id=?", (uid,))
    return bool(r and r["consent"])


def set_consent(uid):
    run("UPDATE users SET consent=1 WHERE id=?", (uid,))


def deactivate(uid):
    run("UPDATE users SET active=0 WHERE id=?", (uid,))


def user_stats():
    day = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")
    week = (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")
    st = {
        "total": one("SELECT COUNT(*) c FROM users")["c"],
        "active": one("SELECT COUNT(*) c FROM users WHERE active=1")["c"],
        "day": one("SELECT COUNT(*) c FROM users WHERE joined_at>=?", (day,))["c"],
        "week": one("SELECT COUNT(*) c FROM users WHERE joined_at>=?", (week,))["c"],
    }
    st["left"] = st["total"] - st["active"]
    st["langs"] = {r["lang"] or "—": r["c"] for r in
                   q("SELECT lang, COUNT(*) c FROM users WHERE active=1 GROUP BY lang")}
    return st


def audience(aud):
    if aud == "all":
        rows = q("SELECT id FROM users WHERE active=1")
    else:
        rows = q("SELECT id FROM users WHERE active=1 AND lang=?", (aud,))
    return [r["id"] for r in rows]


def count_audience(aud):
    return len(audience(aud))


def list_users(offset, limit):
    return q("SELECT * FROM users ORDER BY joined_at DESC, id DESC LIMIT ? OFFSET ?", (limit, offset))


def all_users():
    return q("SELECT * FROM users ORDER BY joined_at")


# ---------------------------------------------------------------- admins
def is_owner(uid):
    return bool(config.OWNER_ID) and uid == config.OWNER_ID


def is_admin(uid):
    return is_owner(uid) or one("SELECT 1 FROM admins WHERE user_id=?", (uid,)) is not None


def admin_ids():
    ids = {r["user_id"] for r in q("SELECT user_id FROM admins")}
    if config.OWNER_ID:
        ids.add(config.OWNER_ID)
    return ids


def add_admin(uid, name, by):
    run("INSERT OR IGNORE INTO admins(user_id, name, added_by, added_at) VALUES(?,?,?,?)", (uid, name or "", by, now()))


def remove_admin(uid):
    run("DELETE FROM admins WHERE user_id=?", (uid,))


def list_admins():
    return q("SELECT * FROM admins ORDER BY added_at")


def user_name(uid):
    r = one("SELECT first_name, username FROM users WHERE id=?", (uid,))
    if not r:
        return str(uid)
    return (r["first_name"] or "") + (f" @{r['username']}" if r["username"] else "") or str(uid)


def new_invite(by):
    token = secrets.token_urlsafe(8)
    run("INSERT INTO invites(token, created_by, created_at) VALUES(?,?,?)", (token, by, now()))
    return token


def use_invite(token, uid):
    r = one("SELECT 1 FROM invites WHERE token=? AND used_by IS NULL", (token,))
    if not r:
        return False
    run("UPDATE invites SET used_by=? WHERE token=?", (uid, token))
    return True


# ---------------------------------------------------------------- catalogue
def categories(grp=None):
    if grp:
        return q("SELECT * FROM categories WHERE grp=? ORDER BY sort", (grp,))
    return q("SELECT * FROM categories ORDER BY sort")


def get_cat(cid):
    return one("SELECT * FROM categories WHERE id=?", (cid,))


def services(cat_id, active_only=True):
    sql = "SELECT * FROM services WHERE cat_id=?" + (" AND active=1" if active_only else "") + " ORDER BY sort, id"
    return q(sql, (cat_id,))


def get_service(sid):
    return one("SELECT * FROM services WHERE id=?", (sid,))


SVC_FIELDS = {"name_ru", "name_es", "name_en", "price", "price_from", "old_price",
              "note_ru", "note_es", "note_en", "confirmed", "active",
              "desc_ru", "desc_es", "desc_en", "needs_review", "admin_note"}


def set_service(sid, field, value):
    if field not in SVC_FIELDS:
        raise ValueError(field)
    run(f"UPDATE services SET {field}=? WHERE id=?", (value, sid))


def add_service(cat_id, name_ru):
    r = one("SELECT COALESCE(MAX(sort),0)+1 n FROM services WHERE cat_id=?", (cat_id,))
    return run("INSERT INTO services(cat_id, sort, name_ru) VALUES(?,?,?)", (cat_id, r["n"], name_ru))


def del_service(sid):
    run("DELETE FROM services WHERE id=?", (sid,))


# ---------------------------------------------------------------- texts
def text_row(key):
    return one("SELECT * FROM texts WHERE key=?", (key,))


def all_texts():
    return q("SELECT * FROM texts ORDER BY sort, key")


def get_text(key, lang):
    """Client-facing text. Empty if missing or flagged 'needs specialist review'."""
    r = text_row(key)
    if not r or r["needs_review"]:
        return ""
    return (r[lang] if lang in ("ru", "es", "en") else "") or r["ru"] or ""


def set_text(key, lang, val):
    if lang not in ("ru", "es", "en"):
        raise ValueError(lang)
    run(f"UPDATE texts SET {lang}=? WHERE key=?", (val, key))


def set_text_all(key, val):
    run("UPDATE texts SET ru=?, es=?, en=? WHERE key=?", (val, val, val, key))


def toggle_text_review(key):
    run("UPDATE texts SET needs_review = 1 - needs_review WHERE key=?", (key,))


# ---------------------------------------------------------------- media
def add_media(kind, file_id, caption):
    return run("INSERT INTO media(kind, file_id, caption, added_at) VALUES(?,?,?,?)", (kind, file_id, caption, now()))


def list_media(kind, limit=10):
    return q("SELECT * FROM media WHERE kind=? ORDER BY id DESC LIMIT ?", (kind, limit))


def count_media(kind):
    return one("SELECT COUNT(*) c FROM media WHERE kind=?", (kind,))["c"]


def del_media(mid):
    run("DELETE FROM media WHERE id=?", (mid,))


# ---------------------------------------------------------------- bookings
STATUSES = ("new", "in_progress", "confirmed", "rescheduled", "cancelled")


def add_booking(user_id, name, phone, service, service_id, wanted, lang, comment):
    return run("""INSERT INTO bookings(user_id, name, phone, service, service_id, wanted, lang, comment, created_at)
                  VALUES(?,?,?,?,?,?,?,?,?)""",
               (user_id, name, phone, service, service_id, wanted, lang, comment, now()))


def get_booking(bid):
    return one("SELECT * FROM bookings WHERE id=?", (bid,))


def list_bookings(status, offset, limit):
    return q("SELECT * FROM bookings WHERE status=? ORDER BY id DESC LIMIT ? OFFSET ?", (status, limit, offset))


def count_bookings(status):
    return one("SELECT COUNT(*) c FROM bookings WHERE status=?", (status,))["c"]


def set_booking(bid, status, confirmed_at=None):
    if confirmed_at is None:
        run("UPDATE bookings SET status=? WHERE id=?", (status, bid))
    else:
        run("UPDATE bookings SET status=?, confirmed_at=? WHERE id=?", (status, confirmed_at, bid))


def log_broadcast(admin_id, aud, sent, failed):
    run("INSERT INTO broadcasts(admin_id, audience, sent, failed, created_at) VALUES(?,?,?,?,?)",
        (admin_id, aud, sent, failed, now()))


# ---------------------------------------------------------------- meta
def get_meta(key, default=""):
    r = one("SELECT value FROM meta WHERE key=?", (key,))
    return r["value"] if r else default


def set_meta(key, value):
    run("INSERT INTO meta(key, value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, value))
