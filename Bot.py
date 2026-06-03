#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🎬 TOMOSHA VAQTI BOT - @TomoshaVaqti_bot
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Dasturchi: @salohiddinWebDev
Versiya: 3.0 PREMIUM
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Yangiliklar v3.0:
  ✅ Ombor (guruh) avtomatik qo'shish - guruh linkini/IDsini yuborish yetarli
  ✅ Database nusxalash - JSON fayl sifatida yuklab olish (HAMMA narsa: kinolar, foydalanuvchilar, adminlar, kanallar, ombor, bloklangan)
  ✅ Database qo'shish - JSON fayl orqali import qilish
  ✅ Super-ega (8505118420) hech kim admin ligidan chiqara olmaydi
  ✅ Support tugmasi - @salohiddinWebDev lichkasiga yo'naltiradi
  ✅ Ertalab 08:00 va kechqurun 20:00 da barcha foydalanuvchilarga /start xabari
  ✅ Kunlik broadcast natijasi adminga yuboriladi
  ✅ Kino tavsifi qo'shish (ixtiyoriy, skip mumkin)
  ✅ AlwaysData free tier uchun optimallashtirilgan (CPU yuk minimal)
"""

import logging
import time
import asyncio
import json
import io
from datetime import datetime, timedelta
from collections import defaultdict
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    filters, ContextTypes
)
from telegram.error import TelegramError, Forbidden

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ⚙️  SOZLAMALAR
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
BOT_TOKEN = "8207727623:AAFf03xoop6lTWhngoejm6d_MfCBLzy5bE4"
BOT_USERNAME = "TomoshaVaqti_bot"
DEVELOPER_USERNAME = "@salohiddinWebDev"
DEVELOPER_ID = 8505118420   # Super-ega: hech kim uni adminlikdan chiqara olmaydi

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 📊 LOGGING (minimal - CPU tejash uchun)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.WARNING   # INFO dan WARNING ga o'zgartirildi - CPU tejash
)
logger = logging.getLogger(__name__)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 💾 MA'LUMOTLAR BAZASI (xotirada)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# 🎬 Kinolar: {raqam: {"message_id": int, "chat_id": int, "nomi": str, "tavsif": str, "qoshilgan": str}}
movies_db = {}

# 👥 Foydalanuvchilar: {user_id: {"ism": str, "username": str, "qoshilgan": str, "faol": bool}}
users_db = {}

# 🚫 Bloklangan foydalanuvchilar: {user_id: {"sabab": str, "vaqt": str}}
blocked_users = {}

# ⏱️ Spam bloklash
spam_tracker = defaultdict(lambda: {"hisoblagich": 0, "birinchi_vaqt": 0, "blok_vaqti": 0})

# 📢 Majburiy kanallar: {channel_id: {"nomi": str, "link": str, "qoshilgan": str}}
required_channels = {}

# 🎬 Ombor guruhlar: {chat_id: {"nomi": str, "link": str, "qoshilgan": str}}
storage_groups = {}

# 👑 Adminlar: {user_id: {"ism": str, "qoshilgan": str}}
admins_db = {DEVELOPER_ID: {"ism": "Super-Ega", "qoshilgan": str(datetime.now().strftime("%d.%m.%Y"))}}

# 📈 Statistika
stats = {
    "jami_foydalanuvchilar": 0,
    "bugungi_foydalanuvchilar": set(),
    "jami_sorovlar": 0,
    "bugungi_sorovlar": 0,
    "bugungi_sana": datetime.now().strftime("%d.%m.%Y"),
    "kanal_statistika": defaultdict(int),
    "botni_bloklaganlar": set(),
}

# 🔄 Admin holati: {admin_id: holat_dict}
admin_state = {}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 🛠️  YORDAMCHI FUNKSIYALAR
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def is_admin(user_id: int) -> bool:
    return user_id in admins_db or user_id == DEVELOPER_ID

def is_super_owner(user_id: int) -> bool:
    """Super-ega tekshiruvi"""
    return user_id == DEVELOPER_ID

def is_spam_blocked(user_id: int) -> bool:
    tracker = spam_tracker[user_id]
    if tracker["blok_vaqti"] > 0:
        if time.time() - tracker["blok_vaqti"] < 60:
            return True
        else:
            spam_tracker[user_id] = {"hisoblagich": 0, "birinchi_vaqt": 0, "blok_vaqti": 0}
            return False
    return False

def check_spam(user_id: int) -> bool:
    if is_admin(user_id):
        return False
    tracker = spam_tracker[user_id]
    current_time = time.time()
    if tracker["blok_vaqti"] > 0:
        if current_time - tracker["blok_vaqti"] < 60:
            return True
        else:
            spam_tracker[user_id] = {"hisoblagich": 0, "birinchi_vaqt": 0, "blok_vaqti": 0}
    if tracker["hisoblagich"] == 0 or current_time - tracker["birinchi_vaqt"] > 10:
        spam_tracker[user_id] = {"hisoblagich": 1, "birinchi_vaqt": current_time, "blok_vaqti": 0}
        return False
    tracker["hisoblagich"] += 1
    if tracker["hisoblagich"] >= 6:
        tracker["blok_vaqti"] = current_time
        return True
    return False

def update_stats_day():
    today = datetime.now().strftime("%d.%m.%Y")
    if stats["bugungi_sana"] != today:
        stats["bugungi_sana"] = today
        stats["bugungi_foydalanuvchilar"] = set()
        stats["bugungi_sorovlar"] = 0

def register_user(user):
    update_stats_day()
    user_id = user.id
    if user_id not in users_db:
        users_db[user_id] = {
            "ism": user.first_name or "Noma'lum",
            "username": f"@{user.username}" if user.username else "Yo'q",
            "qoshilgan": datetime.now().strftime("%d.%m.%Y %H:%M"),
            "faol": True,
        }
        stats["jami_foydalanuvchilar"] += 1
    else:
        users_db[user_id]["faol"] = True
        users_db[user_id]["ism"] = user.first_name or users_db[user_id]["ism"]
        if user.username:
            users_db[user_id]["username"] = f"@{user.username}"
    stats["bugungi_foydalanuvchilar"].add(user_id)

async def check_channels_membership(bot, user_id: int) -> tuple[bool, list]:
    if not required_channels:
        return True, []
    not_subscribed = []
    for channel_id, channel_info in required_channels.items():
        try:
            member = await bot.get_chat_member(channel_id, user_id)
            if member.status in ['left', 'kicked', 'banned']:
                not_subscribed.append(channel_info)
        except TelegramError:
            not_subscribed.append(channel_info)
    return len(not_subscribed) == 0, not_subscribed

def get_subscription_keyboard(not_subscribed_channels: list) -> InlineKeyboardMarkup:
    keyboard = []
    for ch in not_subscribed_channels:
        keyboard.append([InlineKeyboardButton(f"📢 {ch['nomi']}", url=ch['link'])])
    keyboard.append([InlineKeyboardButton("✅ Tekshirish", callback_data="check_subscription")])
    return InlineKeyboardMarkup(keyboard)

def get_main_keyboard(user_id: int) -> ReplyKeyboardMarkup:
    if is_admin(user_id):
        return get_admin_keyboard()
    return get_user_keyboard()

def get_user_keyboard() -> ReplyKeyboardMarkup:
    keyboard = [
        [KeyboardButton("🎬 Kino Qidirish")],
        [KeyboardButton("💬 Support")],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_admin_keyboard() -> ReplyKeyboardMarkup:
    keyboard = [
        [KeyboardButton("🎬 Kino Qo'shish"), KeyboardButton("🗑️ Kino O'chirish")],
        [KeyboardButton("📢 Kanal Qo'shish"), KeyboardButton("📛 Kanal O'chirish")],
        [KeyboardButton("🏪 Ombor Qo'shish"), KeyboardButton("🗂️ Ombor Ko'rish")],
        [KeyboardButton("💾 DB Nusxalash"), KeyboardButton("📥 DB Qo'shish")],
        [KeyboardButton("📊 Statistika"), KeyboardButton("📅 Kunlik Statistika")],
        [KeyboardButton("📣 Reklama Yuborish"), KeyboardButton("👥 Foydalanuvchilar")],
        [KeyboardButton("🚫 Foydalanuvchi Bloklash"), KeyboardButton("✅ Blokni Ochish")],
        [KeyboardButton("👑 Admin Qo'shish"), KeyboardButton("🎬 Kino Qidirish")],
        [KeyboardButton("⚙️ Bot Sozlamalari")],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def remaining_block_time(user_id: int) -> int:
    tracker = spam_tracker[user_id]
    if tracker["blok_vaqti"] > 0:
        elapsed = time.time() - tracker["blok_vaqti"]
        remaining = 60 - elapsed
        return max(0, int(remaining))
    return 0

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 💾 DATABASE NUSXALASH / QO'SHISH
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def export_database() -> dict:
    """Barcha ma'lumotlarni (kinolar, foydalanuvchilar, adminlar, kanallar, ombor, bloklangan) JSON formatida qaytaradi"""
    return {
        "version": "3.0",
        "export_vaqt": datetime.now().strftime("%d.%m.%Y %H:%M"),
        "jami_kinolar": len(movies_db),
        "jami_foydalanuvchilar": len(users_db),
        "kinolar": movies_db,
        "foydalanuvchilar": {str(k): v for k, v in users_db.items()},
        "adminlar": {str(k): v for k, v in admins_db.items()},
        "majburiy_kanallar": {str(k): v for k, v in required_channels.items()},
        "ombor_guruhlar": {str(k): v for k, v in storage_groups.items()},
        "bloklangan_foydalanuvchilar": {str(k): v for k, v in blocked_users.items()},
        "statistika": {
            "jami_foydalanuvchilar": stats["jami_foydalanuvchilar"],
            "jami_sorovlar": stats["jami_sorovlar"],
            "botni_bloklaganlar": list(stats["botni_bloklaganlar"]),
        }
    }

def import_database(data: dict) -> tuple[int, int, int, int, int, int, list]:
    """
    JSON dan barcha ma'lumotlarni import qiladi.
    Qaytaradi: (kinolar_qoshildi, foydalanuvchilar_qoshildi, adminlar_qoshildi,
                kanallar_qoshildi, ombor_qoshildi, xato_soni, xato_list)
    """
    kinolar_qoshildi = 0
    foydalanuvchilar_qoshildi = 0
    adminlar_qoshildi = 0
    kanallar_qoshildi = 0
    ombor_qoshildi = 0
    xato = 0
    xatolar = []

    # Kinolar
    kinolar = data.get("kinolar", {})
    for raqam, info in kinolar.items():
        try:
            if "message_id" not in info or "chat_id" not in info:
                xatolar.append(f"#{raqam}: message_id yoki chat_id yo'q")
                xato += 1
                continue
            if raqam not in movies_db:
                movies_db[raqam] = {
                    "message_id": int(info["message_id"]),
                    "chat_id": int(info["chat_id"]),
                    "nomi": info.get("nomi", f"Kino_{raqam}"),
                    "tavsif": info.get("tavsif", ""),
                    "qoshilgan": info.get("qoshilgan", datetime.now().strftime("%d.%m.%Y %H:%M")),
                }
                kinolar_qoshildi += 1
        except Exception as e:
            xatolar.append(f"#{raqam}: {str(e)}")
            xato += 1

    # Foydalanuvchilar
    foydalanuvchilar = data.get("foydalanuvchilar", {})
    for uid_str, uinfo in foydalanuvchilar.items():
        try:
            uid = int(uid_str)
            if uid not in users_db:
                users_db[uid] = uinfo
                foydalanuvchilar_qoshildi += 1
                stats["jami_foydalanuvchilar"] += 1
        except Exception as e:
            xatolar.append(f"User {uid_str}: {str(e)}")
            xato += 1

    # Adminlar
    adminlar = data.get("adminlar", {})
    for aid_str, ainfo in adminlar.items():
        try:
            aid = int(aid_str)
            if aid not in admins_db:
                admins_db[aid] = ainfo
                adminlar_qoshildi += 1
        except Exception as e:
            xatolar.append(f"Admin {aid_str}: {str(e)}")
            xato += 1

    # Majburiy kanallar
    kanallar = data.get("majburiy_kanallar", {})
    for cid_str, cinfo in kanallar.items():
        try:
            cid = int(cid_str)
            if cid not in required_channels:
                required_channels[cid] = cinfo
                kanallar_qoshildi += 1
        except Exception as e:
            xatolar.append(f"Kanal {cid_str}: {str(e)}")
            xato += 1

    # Ombor guruhlar
    omborlar = data.get("ombor_guruhlar", {})
    for gid_str, ginfo in omborlar.items():
        try:
            gid = int(gid_str)
            if gid not in storage_groups:
                storage_groups[gid] = ginfo
                ombor_qoshildi += 1
        except Exception as e:
            xatolar.append(f"Ombor {gid_str}: {str(e)}")
            xato += 1

    # Bloklangan foydalanuvchilar
    bloklanganlar = data.get("bloklangan_foydalanuvchilar", {})
    for bid_str, binfo in bloklanganlar.items():
        try:
            bid = int(bid_str)
            if bid not in blocked_users:
                blocked_users[bid] = binfo
        except Exception as e:
            xatolar.append(f"Bloklangan {bid_str}: {str(e)}")
            xato += 1

    # Statistika
    old_stats = data.get("statistika", {})
    if old_stats.get("jami_sorovlar", 0) > stats["jami_sorovlar"]:
        stats["jami_sorovlar"] = old_stats["jami_sorovlar"]
    for bid in old_stats.get("botni_bloklaganlar", []):
        try:
            stats["botni_bloklaganlar"].add(int(bid))
        except Exception:
            pass

    return kinolar_qoshildi, foydalanuvchilar_qoshildi, adminlar_qoshildi, kanallar_qoshildi, ombor_qoshildi, xato, xatolar

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 📅 KUNLIK BROADCAST (08:00 va 20:00)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def daily_broadcast(context: ContextTypes.DEFAULT_TYPE):
    now = datetime.now()
    soat = now.hour
    if soat not in [8, 20]:
        return

    broadcast_text = """🎬 <b>/start /start /start /start /start</b>

╔══════════════════════════╗
║   🍿 <b>Tomosha Vaqti Bot</b> 🍿   ║
╚══════════════════════════╝

👋 Kino ko'rish vaqti keldi!
🔢 Kino raqamini yuboring va tomosha qiling!

━━━━━━━━━━━━━━━━━━━━━━━━
🎯 /start bosing yoki raqam yuboring!"""

    sent_count = 0
    failed_count = 0
    blocked_count = 0
    yuborilgan_idlar = []

    for uid in list(users_db.keys()):
        if uid in blocked_users:
            continue
        if is_admin(uid):
            continue
        try:
            await context.bot.send_message(uid, broadcast_text, parse_mode="HTML")
            sent_count += 1
            yuborilgan_idlar.append(uid)
            await asyncio.sleep(0.1)
        except Forbidden:
            blocked_count += 1
            stats["botni_bloklaganlar"].add(uid)
            if uid in users_db:
                users_db[uid]["faol"] = False
        except TelegramError:
            failed_count += 1

    natija_text = f"""📣 <b>Kunlik Broadcast Natijasi</b>

╔══════════════════════════╗
║  📊 <b>BROADCAST HISOBOTI</b>  ║
╚══════════════════════════╝

🕐 <b>Vaqt:</b> {now.strftime("%d.%m.%Y %H:%M")}
{"🌅 Ertalabgi" if soat == 8 else "🌆 Kechqurungi"} broadcast

✅ <b>Muvaffaqiyatli:</b> {sent_count} ta
🚫 <b>Bot bloklagan:</b> {blocked_count} ta
❌ <b>Xatolik:</b> {failed_count} ta

━━━━━━━━━━━━━━━━━━━━━━━━
📝 <b>Yuborilgan foydalanuvchilar IDlari:</b>
<code>{', '.join(str(i) for i in yuborilgan_idlar[:50])}</code>{"..." if len(yuborilgan_idlar) > 50 else ""}

📈 Jami: {sent_count + blocked_count + failed_count} ta urinish"""

    for admin_id in list(admins_db.keys()):
        try:
            await context.bot.send_message(admin_id, natija_text, parse_mode="HTML")
        except Exception:
            pass

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 🎬 XABARLAR MATNI
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

WELCOME_TEXT = """🎬 <b>TOMOSHA VAQTI'ga xush kelibsiz!</b>

╔══════════════════════════╗
║   🍿 <b>Tomosha Vaqti Bot</b> 🍿   ║
╚══════════════════════════╝

Salom, <b>{ism}</b>! 👋

🌟 Bu bot orqali siz:
   ✦ Minglab kinolarni topishingiz
   ✦ Eng sara filmlarni yuklab olishingiz
   ✦ Yangi kinolardan xabardor bo'lishingiz mumkin!

🎯 <b>Qanday foydalanish kerak?</b>
━━━━━━━━━━━━━━━━━━━━━━━━
📌 Kino raqamini yuboring → Film sizga keladi!
📌 Raqamni bilmasangiz → Kino qidiring

🔢 <b>Misol:</b> <code>1001</code> → Film yuboriladi

━━━━━━━━━━━━━━━━━━━━━━━━
💫 <i>Tomosha Vaqti — eng yaxshi kinolar bir joyda!</i>"""

SUBSCRIPTION_REQUIRED_TEXT = """🔐 <b>Diqqat! Obuna talab qilinadi</b>

╔══════════════════════════╗
║  📢 <b>MAJBURIY OBUNA</b> 📢    ║
╚══════════════════════════╝

Salom, <b>{ism}</b>! 👋

Botdan to'liq foydalanish uchun quyidagi
kanallarga obuna bo'lishingiz kerak:

{kanallar}

✅ <b>Obuna bo'lganingizdan so'ng</b>
"Tekshirish" tugmasini bosing!

━━━━━━━━━━━━━━━━━━━━━━━━
💡 <i>Kanallarimizda yangi kinolar, 
   xabarlar va ko'p qiziqarli narsalar bor!</i>"""

SPAM_BLOCKED_TEXT = """🚫 <b>Siz vaqtincha bloklangansiz!</b>

╔══════════════════════════╗
║   ⏱️ <b>SPAM ANIQLANDI</b> ⏱️   ║
╚══════════════════════════╝

Siz juda ko'p xabar yubordingiz!
Spam himoya tizimi sizni avtomatik blokladi.

⏳ <b>Blok muddati:</b> <code>{vaqt}</code> soniya qoldi

━━━━━━━━━━━━━━━━━━━━━━━━
⏱️ <i>Sabr qiling, ko'p o'tmay blok ochiladi!</i>"""

ADMIN_BLOCKED_TEXT = """🚫 <b>Sizga kirish taqiqlangan!</b>

╔══════════════════════════╗
║  🔒 <b>ADMIN BLOKLASH</b> 🔒    ║
╚══════════════════════════╝

Siz <b>adminlar tomonidan</b> bloklangansiz
va botdan foydalana olmaysiz.

📞 <b>Murojaat qilish uchun:</b>
👨‍💻 Dasturchi: {developer}

━━━━━━━━━━━━━━━━━━━━━━━━
⚠️ <i>Agar bu xato deb hisoblasangiz,
   dasturchi bilan bog'laning!</i>"""

MOVIE_NOT_FOUND_TEXT = """❌ <b>Kino topilmadi!</b>

╔══════════════════════════╗
║  🔍 <b>QIDIRUV NATIJALARI</b>   ║
╚══════════════════════════╝

Siz kiritgan raqam: <code>{raqam}</code>

😕 Afsuski, bu raqam bo'yicha kino
   bazamizda mavjud emas.

💡 <b>Kino so'rash uchun:</b>
"💬 Support" tugmasini bosing!

━━━━━━━━━━━━━━━━━━━━━━━━
🍿 <i>Boshqa kinolarni ham ko'rib chiqing!</i>"""

SUGGEST_MOVIE_TEXT = """💬 <b>Adminga Xabar Yuborish</b>

╔══════════════════════════╗
║  🎬 <b>XABAR YUBORISH</b> 🎬    ║
╚══════════════════════════╝

Salom! 🌟

⚠️ <b>Diqqat:</b> Bu xabaringiz to'g'ridan-to'g'ri
adminga boradi!

📝 Xabaringizni yuboring:
(Matn, rasm, video — istalgan format)

━━━━━━━━━━━━━━━━━━━━━━━━
💡 <i>Xabaringizni yuboring, adminlar
   ko'rib chiqishadi!</i>"""

SUGGEST_SENT_TEXT = """✅ <b>Xabaringiz adminga yuborildi!</b>

╔══════════════════════════╗
║  📨 <b>MUVAFFAQIYATLI</b> 📨    ║
╚══════════════════════════╝

🎉 Rahmat, <b>{ism}</b>!

Xabaringiz adminlarga muvaffaqiyatli
yuborildi va tez orada ko'rib chiqiladi.

━━━━━━━━━━━━━━━━━━━━━━━━
💫 <i>Tomosha Vaqti jamoasi sizga
   minnatdor! 🙏</i>"""

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 🤖 BOT HANDLERLARI
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    register_user(user)

    if user_id in blocked_users and not is_admin(user_id):
        all_subscribed, not_subscribed = await check_channels_membership(context.bot, user_id)
        if not all_subscribed:
            text = SUBSCRIPTION_REQUIRED_TEXT.format(
                ism=user.first_name,
                kanallar="\n".join([f"   📌 <b>{ch['nomi']}</b>" for ch in not_subscribed])
            )
            await update.message.reply_text(text, reply_markup=get_subscription_keyboard(not_subscribed), parse_mode="HTML")
            return
        await update.message.reply_text(ADMIN_BLOCKED_TEXT.format(developer=DEVELOPER_USERNAME), parse_mode="HTML")
        return

    all_subscribed, not_subscribed = await check_channels_membership(context.bot, user_id)
    if not all_subscribed and not is_admin(user_id):
        text = SUBSCRIPTION_REQUIRED_TEXT.format(
            ism=user.first_name,
            kanallar="\n".join([f"   📌 <b>{ch['nomi']}</b>" for ch in not_subscribed])
        )
        await update.message.reply_text(text, reply_markup=get_subscription_keyboard(not_subscribed), parse_mode="HTML")
        return

    text = WELCOME_TEXT.format(ism=user.first_name)
    await update.message.reply_text(text, reply_markup=get_main_keyboard(user_id), parse_mode="HTML")

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    user_id = user.id
    data = query.data
    await query.answer()

    if data == "check_subscription":
        all_subscribed, not_subscribed = await check_channels_membership(context.bot, user_id)
        if all_subscribed:
            if user_id in blocked_users and not is_admin(user_id):
                await query.edit_message_text(ADMIN_BLOCKED_TEXT.format(developer=DEVELOPER_USERNAME), parse_mode="HTML")
                return
            await query.edit_message_text(
                f"""✅ <b>Tabriklaymiz!</b>

╔══════════════════════════╗
║  🎉 <b>OBUNA TASDIQLANDI</b> 🎉  ║
╚══════════════════════════╝

Salom, <b>{user.first_name}</b>! 🌟

Siz barcha majburiy kanallarga 
obuna bo'ldingiz!

🎬 Endi botdan to'liq foydalana olasiz.
Raqam yuboring va kino oling!

━━━━━━━━━━━━━━━━━━━━━━━━
🍿 <i>Tomosha Vaqti sizni kutmoqda!</i>""",
                parse_mode="HTML"
            )
            await context.bot.send_message(
                user_id,
                WELCOME_TEXT.format(ism=user.first_name),
                reply_markup=get_main_keyboard(user_id),
                parse_mode="HTML"
            )
        else:
            text = SUBSCRIPTION_REQUIRED_TEXT.format(
                ism=user.first_name,
                kanallar="\n".join([f"   📌 <b>{ch['nomi']}</b>" for ch in not_subscribed])
            )
            await query.edit_message_text(text, reply_markup=get_subscription_keyboard(not_subscribed), parse_mode="HTML")
        return

    if not is_admin(user_id):
        return

    if data.startswith("confirm_delete_movie_"):
        movie_id = data.replace("confirm_delete_movie_", "")
        if movie_id in movies_db:
            movie_name = movies_db[movie_id]["nomi"]
            del movies_db[movie_id]
            await query.edit_message_text(
                f"""✅ <b>Kino o'chirildi!</b>

🔢 <b>Raqam:</b> <code>{movie_id}</code>
🎬 <b>Film:</b> {movie_name}

📊 Jami kinolar: <b>{len(movies_db)}</b> ta""",
                parse_mode="HTML"
            )
        else:
            await query.edit_message_text("❌ Kino topilmadi yoki allaqachon o'chirilgan!")
        return

    if data == "cancel_delete_movie":
        await query.edit_message_text("❌ <b>Bekor qilindi!</b>\n\nKino o'chirish amali bekor qilindi.", parse_mode="HTML")
        return

    if data.startswith("confirm_delete_channel_"):
        ch_id = int(data.replace("confirm_delete_channel_", ""))
        if ch_id in required_channels:
            ch_name = required_channels[ch_id]["nomi"]
            del required_channels[ch_id]
            await query.edit_message_text(
                f"""✅ <b>Kanal o'chirildi!</b>

📛 <b>Kanal:</b> {ch_name}
📢 Jami kanallar: <b>{len(required_channels)}</b> ta""",
                parse_mode="HTML"
            )
        else:
            await query.edit_message_text("❌ Kanal topilmadi!")
        return

    if data == "cancel_delete_channel":
        await query.edit_message_text("❌ Kanal o'chirish bekor qilindi.")
        return

    if data.startswith("confirm_block_user_"):
        uid = int(data.replace("confirm_block_user_", ""))
        if uid not in blocked_users:
            blocked_users[uid] = {
                "sabab": "Admin tomonidan bloklandi",
                "vaqt": datetime.now().strftime("%d.%m.%Y %H:%M")
            }
            user_info = users_db.get(uid, {})
            await query.edit_message_text(
                f"""🚫 <b>Foydalanuvchi bloklandi!</b>

👤 <b>ID:</b> <code>{uid}</code>
👤 <b>Ism:</b> {user_info.get('ism', "Noma'lum")}
📅 <b>Vaqt:</b> {datetime.now().strftime("%d.%m.%Y %H:%M")}""",
                parse_mode="HTML"
            )
        else:
            await query.edit_message_text("⚠️ Bu foydalanuvchi allaqachon bloklangan!")
        return

    if data.startswith("cancel_block_user"):
        await query.edit_message_text("❌ Bloklash bekor qilindi.")
        return

    # ━━━ ADMIN O'CHIRISH (faqat super-ega qila oladi) ━━━
    if data.startswith("confirm_remove_admin_"):
        if not is_super_owner(user_id):
            await query.edit_message_text("❌ Faqat super-ega admin o'chira oladi!")
            return
        target_id = int(data.replace("confirm_remove_admin_", ""))
        if target_id == DEVELOPER_ID:
            await query.edit_message_text("❌ Super-egani adminlikdan chiqarib bo'lmaydi!")
            return
        if target_id in admins_db:
            del admins_db[target_id]
            await query.edit_message_text(
                f"""✅ <b>Admin o'chirildi!</b>

🆔 <b>ID:</b> <code>{target_id}</code>
👑 Qolgan adminlar: <b>{len(admins_db)}</b> ta""",
                parse_mode="HTML"
            )
        return

    if data == "cancel_remove_admin":
        await query.edit_message_text("❌ Admin o'chirish bekor qilindi.")
        return

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return

    user = update.effective_user
    user_id = user.id
    message = update.message
    text = message.text or ""

    register_user(user)

    # ━━━ SPAM TEKSHIRUVI ━━━
    if check_spam(user_id) and not is_admin(user_id):
        remaining = remaining_block_time(user_id)
        await message.reply_text(SPAM_BLOCKED_TEXT.format(vaqt=remaining), parse_mode="HTML")
        return

    stats["jami_sorovlar"] += 1
    stats["bugungi_sorovlar"] += 1

    # ━━━ ADMIN HOLATI ━━━
    if is_admin(user_id) and user_id in admin_state:
        await handle_admin_state(update, context, text)
        return

    # ━━━ ADMIN BLOKLASH ━━━
    if user_id in blocked_users and not is_admin(user_id):
        all_subscribed, not_subscribed = await check_channels_membership(context.bot, user_id)
        if not all_subscribed:
            sub_text = SUBSCRIPTION_REQUIRED_TEXT.format(
                ism=user.first_name,
                kanallar="\n".join([f"   📌 <b>{ch['nomi']}</b>" for ch in not_subscribed])
            )
            await message.reply_text(sub_text, reply_markup=get_subscription_keyboard(not_subscribed), parse_mode="HTML")
            return
        await message.reply_text(ADMIN_BLOCKED_TEXT.format(developer=DEVELOPER_USERNAME), parse_mode="HTML")
        return

    # ━━━ MAJBURIY KANAL ━━━
    if not is_admin(user_id):
        all_subscribed, not_subscribed = await check_channels_membership(context.bot, user_id)
        if not all_subscribed:
            sub_text = SUBSCRIPTION_REQUIRED_TEXT.format(
                ism=user.first_name,
                kanallar="\n".join([f"   📌 <b>{ch['nomi']}</b>" for ch in not_subscribed])
            )
            await message.reply_text(sub_text, reply_markup=get_subscription_keyboard(not_subscribed), parse_mode="HTML")
            return

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # TUGMALAR
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    # 🎬 KINO QO'SHISH
    if text == "🎬 Kino Qo'shish" and is_admin(user_id):
        admin_state[user_id] = {"holat": "kino_raqam_kutish"}
        await message.reply_text(
            """🎬 <b>Kino Qo'shish</b>

╔══════════════════════════╗
║  ➕ <b>YANGI KINO</b> ➕       ║
╚══════════════════════════╝

📋 <b>Qo'shish jarayoni:</b>
   1️⃣ Raqam yuboring
   2️⃣ Film faylini yuboring (shu chatga yoki ombor guruhiga)
   3️⃣ Tavsif yuboring yoki skip qiling

━━━━━━━━━━━━━━━━━━━━━━━━
🔢 <b>Kino raqamini yuboring:</b>
(Faqat raqam, masalan: <code>1001</code>)

❌ Bekor qilish uchun /cancel""",
            parse_mode="HTML"
        )
        return

    # 🗑️ KINO O'CHIRISH
    if text == "🗑️ Kino O'chirish" and is_admin(user_id):
        if not movies_db:
            await message.reply_text("❌ <b>Bazada kino yo'q!</b>\n\nHozircha hech qanday kino qo'shilmagan.", parse_mode="HTML")
            return
        admin_state[user_id] = {"holat": "kino_ochirish_raqam"}
        movie_list = "\n".join([f"   🎬 <code>{k}</code> — {v['nomi'][:30]}" for k, v in list(movies_db.items())[-20:]])
        await message.reply_text(
            f"""🗑️ <b>Kino O'chirish</b>

╔══════════════════════════╗
║  ❌ <b>KINONI O'CHIRISH</b> ❌  ║
╚══════════════════════════╝

📋 <b>Bazadagi kinolar (oxirgi 20):</b>
{movie_list}

━━━━━━━━━━━━━━━━━━━━━━━━
🔢 <b>O'chirmoqchi bo'lgan kino raqamini yuboring:</b>

❌ Bekor qilish uchun /cancel""",
            parse_mode="HTML"
        )
        return

    # 📢 KANAL QO'SHISH
    if text == "📢 Kanal Qo'shish" and is_admin(user_id):
        admin_state[user_id] = {"holat": "kanal_qoshish_id"}
        await message.reply_text(
            """📢 <b>Majburiy Kanal Qo'shish</b>

╔══════════════════════════╗
║  ➕ <b>KANAL QO'SHISH</b> ➕   ║
╚══════════════════════════╝

ℹ️ Kanal qo'shish uchun botni kanalga
<b>admin</b> qilib qo'ying!

Bot o'zi avtomatik aniqlab qo'shadi.

━━━━━━━━━━━━━━━━━━━━━━━━
📌 <b>Kanal ID yuboring:</b>
(Masalan: <code>-1001234567890</code>)

❌ Bekor qilish uchun /cancel""",
            parse_mode="HTML"
        )
        return

    # 📛 KANAL O'CHIRISH
    if text == "📛 Kanal O'chirish" and is_admin(user_id):
        if not required_channels:
            await message.reply_text("❌ <b>Majburiy kanal yo'q!</b>", parse_mode="HTML")
            return
        ch_list = "\n".join([f"   📢 <code>{k}</code> — {v['nomi']}" for k, v in required_channels.items()])
        admin_state[user_id] = {"holat": "kanal_ochirish_id"}
        await message.reply_text(
            f"""📛 <b>Kanal O'chirish</b>

╔══════════════════════════╗
║  ❌ <b>KANALNI O'CHIRISH</b> ❌  ║
╚══════════════════════════╝

📋 <b>Majburiy kanallar:</b>
{ch_list}

━━━━━━━━━━━━━━━━━━━━━━━━
📌 <b>O'chirmoqchi bo'lgan kanal ID ni yuboring:</b>

❌ Bekor qilish uchun /cancel""",
            parse_mode="HTML"
        )
        return

    # 🏪 OMBOR QO'SHISH
    if text == "🏪 Ombor Qo'shish" and is_admin(user_id):
        admin_state[user_id] = {"holat": "ombor_qoshish"}
        await message.reply_text(
            """🏪 <b>Ombor Guruh Qo'shish</b>

╔══════════════════════════╗
║  🗂️ <b>YANGI OMBOR</b> 🗂️      ║
╚══════════════════════════╝

📋 <b>Ombor nima?</b>
Kinolar saqlanadigan guruh yoki kanal.
Bot o'sha guruhdan foydalanuvchilarga
kino copy qilib yuboradi.

━━━━━━━━━━━━━━━━━━━━━━━━
⚠️ <b>Avval:</b>
1. Guruh/kanalga botni admin qiling
2. Guruh link yoki ID sini yuboring

📌 <b>Link yoki ID yuboring:</b>
Masalan: <code>https://t.me/mening_guruhim</code>
yoki: <code>-1001234567890</code>

❌ Bekor qilish uchun /cancel""",
            parse_mode="HTML"
        )
        return

    # 🗂️ OMBOR KO'RISH
    if text == "🗂️ Ombor Ko'rish" and is_admin(user_id):
        if not storage_groups:
            await message.reply_text(
                """ℹ️ <b>Ombor guruhlar yo'q!</b>

Hali hech qanday ombor qo'shilmagan.
"🏪 Ombor Qo'shish" tugmasini bosing.""",
                parse_mode="HTML"
            )
            return
        grp_list = "\n".join([
            f"   🏪 <code>{gid}</code>\n      📛 {ginfo['nomi']}\n      🔗 {ginfo['link']}"
            for gid, ginfo in storage_groups.items()
        ])
        await message.reply_text(
            f"""🗂️ <b>Ombor Guruhlar</b>

╔══════════════════════════╗
║  🏪 <b>OMBOR RO'YXATI</b> 🏪   ║
╚══════════════════════════╝

📊 Jami: <b>{len(storage_groups)}</b> ta ombor

{grp_list}

━━━━━━━━━━━━━━━━━━━━━━━━
💡 <i>Bot bu guruhlardan kinolarni
   foydalanuvchilarga yuboradi.</i>""",
            parse_mode="HTML"
        )
        return

    # 💾 DATABASE NUSXALASH
    if text == "💾 DB Nusxalash" and is_admin(user_id):
        try:
            db_data = export_database()
            json_str = json.dumps(db_data, ensure_ascii=False, indent=2)
            json_bytes = json_str.encode("utf-8")

            bio = io.BytesIO(json_bytes)
            bio.name = f"database_{datetime.now().strftime('%d-%m-%Y_%H-%M')}.json"

            await message.reply_document(
                document=bio,
                caption=f"""💾 <b>Database To'liq Nusxasi</b>

╔══════════════════════════╗
║  📦 <b>DB NUSXA TAYYOR</b> 📦  ║
╚══════════════════════════╝

📊 <b>Nusxa tarkibi:</b>
🎬 Kinolar: <b>{len(movies_db)}</b> ta
👥 Foydalanuvchilar: <b>{len(users_db)}</b> ta
👑 Adminlar: <b>{len(admins_db)}</b> ta
📢 Majburiy kanallar: <b>{len(required_channels)}</b> ta
🏪 Ombor guruhlar: <b>{len(storage_groups)}</b> ta
🚫 Bloklangan: <b>{len(blocked_users)}</b> ta

📅 <b>Eksport vaqti:</b> {datetime.now().strftime("%d.%m.%Y %H:%M")}

💡 <i>Bu faylni saqlang — xavfsizlik
   nusxasi sifatida ishlatiladi!</i>

🔄 Qayta yuklash uchun:
"📥 DB Qo'shish" tugmasini bosing.""",
                parse_mode="HTML"
            )
        except Exception as e:
            await message.reply_text(f"❌ Xatolik yuz berdi: {str(e)}", parse_mode="HTML")
        return

    # 📥 DATABASE QO'SHISH
    if text == "📥 DB Qo'shish" and is_admin(user_id):
        admin_state[user_id] = {"holat": "db_import_kutish"}
        await message.reply_text(
            f"""📥 <b>Database Import</b>

╔══════════════════════════╗
║  📂 <b>DB QO'SHISH</b> 📂      ║
╚══════════════════════════╝

📋 <b>Qanday ishlaydi:</b>
   1. Avval "💾 DB Nusxalash" bilan fayl oling
   2. Shu faylni shu yerga yuboring
   3. Bot import qiladi va holatini bildiradi

⚠️ <b>Muhim:</b>
   ✦ Faqat .json formatdagi fayl qabul qilinadi
   ✦ Mavjud ma'lumotlar o'zgartirilmaydi
   ✦ Faqat yangi ma'lumotlar qo'shiladi
   ✦ Kinolar, foydalanuvchilar, adminlar,
     kanallar, ombor — hammasi import bo'ladi

━━━━━━━━━━━━━━━━━━━━━━━━
📎 <b>Hozir JSON faylni yuboring:</b>

Joriy bazada:
🎬 Kinolar: <b>{len(movies_db)}</b> ta
👥 Foydalanuvchilar: <b>{len(users_db)}</b> ta

❌ Bekor qilish uchun /cancel""",
            parse_mode="HTML"
        )
        return

    # 📊 STATISTIKA
    if text == "📊 Statistika" and is_admin(user_id):
        update_stats_day()
        faol_users = sum(1 for u in users_db.values() if u.get("faol"))
        ch_stats = ""
        for ch_id, ch_info in required_channels.items():
            count = stats["kanal_statistika"].get(ch_id, 0)
            ch_stats += f"\n   📢 {ch_info['nomi']}: <b>{count}</b> ta"
        await message.reply_text(
            f"""📊 <b>Bot Statistikasi</b>

╔══════════════════════════╗
║  📈 <b>UMUMIY STATISTIKA</b>   ║
╚══════════════════════════╝

👥 <b>Foydalanuvchilar:</b>
   ✦ Jami: <b>{stats['jami_foydalanuvchilar']}</b> ta
   ✦ Faol: <b>{faol_users}</b> ta
   ✦ Bloklangan (admin): <b>{len(blocked_users)}</b> ta
   ✦ Botni bloklagan: <b>{len(stats['botni_bloklaganlar'])}</b> ta

🎬 <b>Kinolar:</b>
   ✦ Jami: <b>{len(movies_db)}</b> ta kino

📨 <b>So'rovlar:</b>
   ✦ Jami: <b>{stats['jami_sorovlar']}</b> ta
   ✦ Bugungi: <b>{stats['bugungi_sorovlar']}</b> ta

🏪 <b>Ombor guruhlar:</b> <b>{len(storage_groups)}</b> ta
📢 <b>Majburiy kanallar:</b> <b>{len(required_channels)}</b> ta{ch_stats}
👑 <b>Adminlar:</b> <b>{len(admins_db)}</b> ta

━━━━━━━━━━━━━━━━━━━━━━━━
📅 <i>Sana: {datetime.now().strftime("%d.%m.%Y %H:%M")}</i>""",
            parse_mode="HTML"
        )
        return

    # 📅 KUNLIK STATISTIKA
    if text == "📅 Kunlik Statistika" and is_admin(user_id):
        update_stats_day()
        await message.reply_text(
            f"""📅 <b>Kunlik Statistika</b>

╔══════════════════════════╗
║  📆 <b>BUGUNGI KUN</b> 📆      ║
╚══════════════════════════╝

📅 <b>Sana:</b> {stats['bugungi_sana']}

👥 <b>Yangi foydalanuvchilar:</b>
   ✦ Bugun qo'shildi: <b>{len(stats['bugungi_foydalanuvchilar'])}</b> ta

📨 <b>So'rovlar:</b>
   ✦ Bugungi: <b>{stats['bugungi_sorovlar']}</b> ta

📈 <b>Umumiy:</b>
   ✦ Jami foydalanuvchilar: <b>{stats['jami_foydalanuvchilar']}</b> ta
   ✦ Jami kinolar: <b>{len(movies_db)}</b> ta

━━━━━━━━━━━━━━━━━━━━━━━━
⏰ <i>Vaqt: {datetime.now().strftime("%H:%M:%S")}</i>""",
            parse_mode="HTML"
        )
        return

    # 📣 REKLAMA YUBORISH
    if text == "📣 Reklama Yuborish" and is_admin(user_id):
        admin_state[user_id] = {"holat": "reklama_kutish"}
        await message.reply_text(
            """📣 <b>Reklama Yuborish</b>

╔══════════════════════════╗
║  📢 <b>OMMAVIY XABAR</b> 📢   ║
╚══════════════════════════╝

📋 <b>Reklama yuborish:</b>
   ✦ Matn, rasm, video, fayl — barchasi mumkin
   ✦ Barcha foydalanuvchilarga yuboriladi

━━━━━━━━━━━━━━━━━━━━━━━━
📨 <b>Reklama xabarini yuboring:</b>

❌ Bekor qilish uchun /cancel""",
            parse_mode="HTML"
        )
        return

    # 👥 FOYDALANUVCHILAR
    if text == "👥 Foydalanuvchilar" and is_admin(user_id):
        users_list = list(users_db.items())[-15:]
        user_text = ""
        for uid, uinfo in users_list:
            blok = "🚫" if uid in blocked_users else "✅"
            user_text += f"\n{blok} <code>{uid}</code> | {uinfo['ism'][:15]} | {uinfo['username']}"
        await message.reply_text(
            f"""👥 <b>Foydalanuvchilar Ro'yxati</b>

╔══════════════════════════╗
║  👤 <b>FOYDALANUVCHILAR</b>    ║
╚══════════════════════════╝

📊 Jami: <b>{len(users_db)}</b> ta
🚫 Bloklangan: <b>{len(blocked_users)}</b> ta

<b>Oxirgi 15 ta:</b>
{user_text}

━━━━━━━━━━━━━━━━━━━━━━━━
✅ = Faol  🚫 = Bloklangan""",
            parse_mode="HTML"
        )
        return

    # 🚫 FOYDALANUVCHI BLOKLASH
    if text == "🚫 Foydalanuvchi Bloklash" and is_admin(user_id):
        admin_state[user_id] = {"holat": "bloklash_id"}
        await message.reply_text(
            """🚫 <b>Foydalanuvchi Bloklash</b>

╔══════════════════════════╗
║  🔒 <b>BLOKLASH</b> 🔒         ║
╚══════════════════════════╝

🔢 <b>Foydalanuvchi ID sini yuboring:</b>

❌ Bekor qilish uchun /cancel""",
            parse_mode="HTML"
        )
        return

    # ✅ BLOKNI OCHISH
    if text == "✅ Blokni Ochish" and is_admin(user_id):
        if not blocked_users:
            await message.reply_text("ℹ️ <b>Bloklangan foydalanuvchi yo'q!</b>", parse_mode="HTML")
            return
        blocked_list = "\n".join([f"   🚫 <code>{uid}</code> — {users_db.get(uid, {}).get('ism', 'Noma\'lum')}" for uid in list(blocked_users.keys())[:20]])
        admin_state[user_id] = {"holat": "blok_ochish_id"}
        await message.reply_text(
            f"""✅ <b>Blokni Ochish</b>

📋 <b>Bloklangan foydalanuvchilar:</b>
{blocked_list}

━━━━━━━━━━━━━━━━━━━━━━━━
🔢 <b>ID sini yuboring:</b>

❌ Bekor qilish uchun /cancel""",
            parse_mode="HTML"
        )
        return

    # 👑 ADMIN QO'SHISH
    if text == "👑 Admin Qo'shish" and is_admin(user_id):
        admin_state[user_id] = {"holat": "admin_qoshish_id"}
        await message.reply_text(
            """👑 <b>Admin Qo'shish</b>

╔══════════════════════════╗
║  👑 <b>YANGI ADMIN</b> 👑      ║
╚══════════════════════════╝

⚠️ <b>Diqqat!</b>
Yangi admin barcha admin imkoniyatlaridan
foydalana oladi!

🔢 <b>Yangi admin Telegram ID sini yuboring:</b>

❌ Bekor qilish uchun /cancel""",
            parse_mode="HTML"
        )
        return

    # ⚙️ BOT SOZLAMALARI
    if text == "⚙️ Bot Sozlamalari" and is_admin(user_id):
        admins_list = "\n".join([
            f"   {'👑 SUPER-EGA' if aid == DEVELOPER_ID else '🔑 Admin'} <code>{aid}</code> — {ainfo['ism']}"
            for aid, ainfo in admins_db.items()
        ])
        extra = ""
        if is_super_owner(user_id):
            extra = "\n\n💡 <i>Admin o'chirish uchun admin ID sidan keyin /removeadmin [ID] yozing</i>"
        await message.reply_text(
            f"""⚙️ <b>Bot Sozlamalari</b>

╔══════════════════════════╗
║  🔧 <b>SOZLAMALAR</b> 🔧       ║
╚══════════════════════════╝

🤖 <b>Bot:</b> @{BOT_USERNAME}
👨‍💻 <b>Dasturchi:</b> {DEVELOPER_USERNAME}

👑 <b>Adminlar:</b>
{admins_list}

📢 <b>Majburiy kanallar:</b> {len(required_channels)} ta
🏪 <b>Ombor guruhlar:</b> {len(storage_groups)} ta
🎬 <b>Kinolar:</b> {len(movies_db)} ta
👥 <b>Foydalanuvchilar:</b> {len(users_db)} ta{extra}

━━━━━━━━━━━━━━━━━━━━━━━━
🔄 <i>Version: 3.0 PREMIUM</i>""",
            parse_mode="HTML"
        )
        return

    # 💬 SUPPORT TUGMASI
    if text == "💬 Support":
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("💬 Support bilan bog'lanish", url="https://t.me/salohiddinWebDev")]
        ])
        await message.reply_text(
            """💬 <b>Support</b>

╔══════════════════════════╗
║  🛠️ <b>SUPPORT XIZMATI</b> 🛠️  ║
╚══════════════════════════╝

Muammo yoki savolingiz bormi?
Quyidagi tugma orqali bog'laning:

👨‍💻 <b>Dasturchi:</b> @salohiddinWebDev

━━━━━━━━━━━━━━━━━━━━━━━━
💡 <i>Tez orada javob beramiz!</i>""",
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        return

    # 🎬 KINO QIDIRISH
    if text == "🎬 Kino Qidirish":
        await message.reply_text(
            """🔍 <b>Kino Qidirish</b>

╔══════════════════════════╗
║  🎬 <b>KINO QIDIRISH</b> 🎬    ║
╚══════════════════════════╝

🔢 <b>Kino raqamini yuboring!</b>
📌 <b>Misol:</b> <code>1001</code>

━━━━━━━━━━━━━━━━━━━━━━━━
💡 <i>Raqamni bilmasangiz, "Support"
   tugmasi orqali so'rang!</i>""",
            parse_mode="HTML"
        )
        return

    # ━━━ RAQAMNI TEKSHIRISH ━━━
    if text and text.strip().isdigit():
        movie_id = text.strip()
        if movie_id in movies_db:
            movie = movies_db[movie_id]
            tavsif = movie.get("tavsif", "")
            try:
                if tavsif:
                    await context.bot.copy_message(
                        chat_id=user_id,
                        from_chat_id=movie["chat_id"],
                        message_id=movie["message_id"],
                        caption=tavsif,
                    )
                else:
                    await context.bot.copy_message(
                        chat_id=user_id,
                        from_chat_id=movie["chat_id"],
                        message_id=movie["message_id"],
                    )
            except TelegramError as e:
                logger.error(f"Copy xatosi: {e}")
                await message.reply_text(
                    "⚠️ <b>Kino yuborishda xatolik!</b>\n\nAdmin bilan bog'laning.",
                    parse_mode="HTML"
                )
        else:
            await message.reply_text(
                f"""❌ <b>Kino topilmadi!</b>

╔══════════════════════════╗
║  🔍 <b>QIDIRUV NATIJALARI</b>   ║
╚══════════════════════════╝

Siz kiritgan raqam: <code>{movie_id}</code>

😕 Afsuski, bu raqam bo'yicha kino
   bazamizda mavjud emas.

💡 <b>Mavjud filmlarni ko'rish uchun:</b>
👉 <a href="https://t.me/Tomosha_Vaqti">@Tomosha_Vaqti</a> kanalga qo'shiling!

━━━━━━━━━━━━━━━━━━━━━━━━
🍿 <i>Boshqa kinolarni ham ko'rib chiqing!</i>""",
                parse_mode="HTML",
                disable_web_page_preview=True
            )
        return

    # ━━━ NOMA'LUM XABAR ━━━
    if not is_admin(user_id):
        user_info = users_db.get(user_id, {"ism": "Noma'lum", "username": "Yo'q"})
        kimdan_text = f"""💬 <b>Yangi Xabar!</b>

╔══════════════════════════╗
║  📨 <b>FOYDALANUVCHI XABARI</b> ║
╚══════════════════════════╝

👤 <b>Kimdan:</b> {user_info.get('ism', "Noma'lum")}
📱 <b>Username:</b> {user_info.get('username', "Yo'q")}
🆔 <b>User ID:</b> <code>{user_id}</code>
📅 <b>Vaqt:</b> {datetime.now().strftime("%d.%m.%Y %H:%M")}

━━━━━━━━━━━━━━━━━━━━━━━━
📝 <b>Xabar matni quyida:</b>"""

        for admin_id in list(admins_db.keys()):
            try:
                await context.bot.send_message(admin_id, kimdan_text, parse_mode="HTML")
                await context.bot.copy_message(
                    chat_id=admin_id,
                    from_chat_id=message.chat_id,
                    message_id=message.message_id,
                )
            except Exception:
                pass

        await message.reply_text(
            """✅ <b>Xabaringiz adminga yuborildi!</b>

╔══════════════════════════╗
║  📨 <b>MUVAFFAQIYATLI</b> 📨    ║
╚══════════════════════════╝

🎉 Rahmat! Xabaringiz adminlarga
muvaffaqiyatli yuborildi.

💡 <b>Mavjud filmlarni ko'rish uchun:</b>
👉 <a href="https://t.me/Tomosha_Vaqti">@Tomosha_Vaqti</a> kanalga qo'shiling!

━━━━━━━━━━━━━━━━━━━━━━━━
📌 Kino olish uchun <b>raqam</b> yuboring.
📌 Masalan: <code>1001</code>""",
            parse_mode="HTML",
            disable_web_page_preview=True
        )

async def handle_admin_state(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
    user = update.effective_user
    user_id = user.id
    message = update.message
    state = admin_state.get(user_id, {})
    holat = state.get("holat", "")

    # ━━━ KINO QO'SHISH ━━━
    if holat == "kino_raqam_kutish":
        if text and text.strip().isdigit():
            raqam = text.strip()
            if raqam in movies_db:
                await message.reply_text(
                    f"""⚠️ <b>Bu raqam allaqachon band!</b>

🔢 Raqam: <code>{raqam}</code>
🎬 Film: {movies_db[raqam]['nomi']}

Boshqa raqam kiriting yoki /cancel""",
                    parse_mode="HTML"
                )
                return

            ombor_royxat = ""
            if storage_groups:
                ombor_royxat = "\n\n📦 <b>Ombordagi filmlar (message_id bo'yicha):</b>\n"
                ombor_royxat += "━━━━━━━━━━━━━━━━━━━━━━━━\n"
                ombor_filmlar = [
                    (k, v) for k, v in movies_db.items()
                    if v.get("chat_id") in storage_groups
                ]
                if ombor_filmlar:
                    for k, v in ombor_filmlar[-30:]:
                        ombor_royxat += f"🎬 <code>{v['message_id']}</code> — {v['nomi'][:35]}\n"
                    ombor_royxat += "\n💡 Yuqoridagi <b>message_id</b> ni yuboring → film qo'shiladi!"
                else:
                    ombor_royxat += "📭 Omborda hali film yo'q.\n💡 Filmni to'g'ridan-to'g'ri yuboring."

            admin_state[user_id] = {"holat": "kino_fayl_yoki_id_kutish", "raqam": raqam}
            await message.reply_text(
                f"""✅ <b>Raqam qabul qilindi!</b>

🔢 <b>Kino raqami:</b> <code>{raqam}</code>

━━━━━━━━━━━━━━━━━━━━━━━━
📤 <b>Endi quyidagilardan birini yuboring:</b>

1️⃣ <b>Filmni to'g'ridan-to'g'ri yuboring</b>
   (Video, rasm, hujjat yoki istalgan format)

2️⃣ <b>Ombordagi filmning message_id sini yuboring</b>
   (Quyidagi ro'yxatdan tanlang){ombor_royxat}

━━━━━━━━━━━━━━━━━━━━━━━━
❌ Bekor qilish uchun /cancel""",
                parse_mode="HTML"
            )
        else:
            await message.reply_text("❌ Faqat raqam yuboring! Masalan: <code>1001</code>", parse_mode="HTML")
        return

    if holat == "kino_fayl_yoki_id_kutish":
        raqam = state.get("raqam")
        movie_name = ""
        saved_message_id = None
        saved_chat_id = None

        if message.text and message.text.strip().isdigit():
            ombor_msg_id = int(message.text.strip())
            existing_movie = None
            for k, v in movies_db.items():
                if v.get("message_id") == ombor_msg_id and v.get("chat_id") in storage_groups:
                    existing_movie = v
                    break

            if existing_movie:
                saved_message_id = ombor_msg_id
                saved_chat_id = existing_movie["chat_id"]
                movie_name = existing_movie["nomi"]
            else:
                if storage_groups:
                    first_grp_id = list(storage_groups.keys())[0]
                    saved_message_id = ombor_msg_id
                    saved_chat_id = first_grp_id
                    movie_name = f"Kino_{raqam}"
                    try:
                        test_msg = await context.bot.copy_message(
                            chat_id=user_id,
                            from_chat_id=first_grp_id,
                            message_id=ombor_msg_id,
                        )
                        try:
                            await context.bot.delete_message(chat_id=user_id, message_id=test_msg.message_id)
                        except Exception:
                            pass
                    except TelegramError as e:
                        await message.reply_text(
                            f"""❌ <b>Bu message_id topilmadi!</b>

🆔 Kiritilgan ID: <code>{ombor_msg_id}</code>

Xatolik: {str(e)}

━━━━━━━━━━━━━━━━━━━━━━━━
💡 To'g'ri message_id ni yuboring yoki
   filmni to'g'ridan-to'g'ri yuboring!""",
                            parse_mode="HTML"
                        )
                        return
                else:
                    await message.reply_text(
                        "❌ <b>Ombor guruh yo'q!</b>\n\nFilmni to'g'ridan-to'g'ri yuboring.",
                        parse_mode="HTML"
                    )
                    return

        elif message.video or message.document or message.photo or message.audio or message.voice or message.video_note:
            if message.video:
                movie_name = message.video.file_name or f"Video_{raqam}"
            elif message.document:
                movie_name = message.document.file_name or f"Fayl_{raqam}"
            elif message.photo:
                movie_name = f"Rasm_{raqam}"
            elif message.audio:
                movie_name = message.audio.file_name or f"Audio_{raqam}"
            else:
                movie_name = f"Kino_{raqam}"
            saved_message_id = message.message_id
            saved_chat_id = message.chat_id
        else:
            await message.reply_text(
                """❌ <b>Noto'g'ri format!</b>

Quyidagilardan birini yuboring:
1️⃣ Film fayli (video, rasm, hujjat)
2️⃣ Ombordagi filmning <b>message_id</b> raqami

❌ Bekor qilish uchun /cancel""",
                parse_mode="HTML"
            )
            return

        # Tavsif so'rash
        admin_state[user_id] = {
            "holat": "kino_tavsif_kutish",
            "raqam": raqam,
            "movie_name": movie_name,
            "saved_message_id": saved_message_id,
            "saved_chat_id": saved_chat_id,
        }
        await message.reply_text(
            f"""✅ <b>Film qabul qilindi!</b>

🔢 <b>Raqam:</b> <code>{raqam}</code>
🎥 <b>Nomi:</b> {movie_name}

━━━━━━━━━━━━━━━━━━━━━━━━
📝 <b>Kino tavsifini yuboring:</b>
(Masalan: "2024-yil eng yaxshi kinosu, janr: drama")

⏭️ Tavsif qo'shmaslik uchun: <b>skip</b> yuboring

❌ Bekor qilish uchun /cancel""",
            parse_mode="HTML"
        )
        return

    # ━━━ KINO TAVSIFI ━━━
    if holat == "kino_tavsif_kutish":
        raqam = state.get("raqam")
        movie_name = state.get("movie_name")
        saved_message_id = state.get("saved_message_id")
        saved_chat_id = state.get("saved_chat_id")

        if text and text.strip().lower() == "skip":
            tavsif = ""
        else:
            tavsif = text.strip() if text else ""

        movies_db[raqam] = {
            "message_id": saved_message_id,
            "chat_id": saved_chat_id,
            "nomi": movie_name,
            "tavsif": tavsif,
            "qoshilgan": datetime.now().strftime("%d.%m.%Y %H:%M"),
        }
        del admin_state[user_id]

        manba = "📦 Ombor" if (saved_chat_id in storage_groups) else "📤 To'g'ridan yuklandi"
        tavsif_ko = f"\n📝 <b>Tavsif:</b> {tavsif}" if tavsif else "\n📝 <b>Tavsif:</b> Yo'q (skip qilindi)"

        await message.reply_text(
            f"""✅ <b>Kino muvaffaqiyatli qo'shildi!</b>

╔══════════════════════════╗
║  🎬 <b>QO'SHILDI</b> 🎬         ║
╚══════════════════════════╝

🔢 <b>Raqam:</b> <code>{raqam}</code>
🎥 <b>Nomi:</b> {movie_name}{tavsif_ko}
📦 <b>Manba:</b> {manba}
📅 <b>Vaqt:</b> {datetime.now().strftime("%d.%m.%Y %H:%M")}

━━━━━━━━━━━━━━━━━━━━━━━━
📊 Jami kinolar: <b>{len(movies_db)}</b> ta

💡 Foydalanuvchi <code>{raqam}</code> raqamini yuborganda
   shu filmni oladi!""",
            parse_mode="HTML"
        )
        return

    # Eski holat nomini qollab-quvvatlash
    if holat == "kino_fayl_kutish":
        raqam = state.get("raqam")
        movie_name = ""
        if message.video:
            movie_name = message.video.file_name or f"Video_{raqam}"
        elif message.document:
            movie_name = message.document.file_name or f"Fayl_{raqam}"
        elif message.photo:
            movie_name = f"Rasm_{raqam}"
        elif message.text:
            movie_name = message.text[:50]
        elif message.audio:
            movie_name = message.audio.file_name or f"Audio_{raqam}"
        else:
            movie_name = f"Kino_{raqam}"

        admin_state[user_id] = {
            "holat": "kino_tavsif_kutish",
            "raqam": raqam,
            "movie_name": movie_name,
            "saved_message_id": message.message_id,
            "saved_chat_id": message.chat_id,
        }
        await message.reply_text(
            f"""✅ <b>Film qabul qilindi!</b>

🔢 <b>Raqam:</b> <code>{raqam}</code>
🎥 <b>Nomi:</b> {movie_name}

━━━━━━━━━━━━━━━━━━━━━━━━
📝 <b>Kino tavsifini yuboring:</b>

⏭️ Skip uchun: <b>skip</b> yuboring

❌ Bekor qilish uchun /cancel""",
            parse_mode="HTML"
        )
        return

    # ━━━ KINO O'CHIRISH ━━━
    if holat == "kino_ochirish_raqam":
        if text and text.strip().isdigit():
            raqam = text.strip()
            if raqam in movies_db:
                movie = movies_db[raqam]
                keyboard = InlineKeyboardMarkup([[
                    InlineKeyboardButton("✅ Ha, o'chir", callback_data=f"confirm_delete_movie_{raqam}"),
                    InlineKeyboardButton("❌ Yo'q, bekor", callback_data="cancel_delete_movie"),
                ]])
                await message.reply_text(
                    f"""🗑️ <b>Kinoni o'chirishni tasdiqlang!</b>

🔢 <b>Raqam:</b> <code>{raqam}</code>
🎬 <b>Film:</b> {movie['nomi']}
📅 <b>Qo'shilgan:</b> {movie['qoshilgan']}

⚠️ Bu amalni qaytarib bo'lmaydi!""",
                    reply_markup=keyboard,
                    parse_mode="HTML"
                )
                del admin_state[user_id]
            else:
                await message.reply_text(f"❌ <code>{text.strip()}</code> raqamli kino topilmadi!", parse_mode="HTML")
        else:
            await message.reply_text("❌ Faqat raqam yuboring!", parse_mode="HTML")
        return

    # ━━━ KANAL QO'SHISH ━━━
    if holat == "kanal_qoshish_id":
        try:
            channel_id = int(text.strip())
            try:
                chat = await context.bot.get_chat(channel_id)
                channel_name = chat.title or chat.username or str(channel_id)
                if chat.username:
                    channel_link = f"https://t.me/{chat.username}"
                else:
                    channel_link = f"https://t.me/c/{str(channel_id).replace('-100', '')}"
                required_channels[channel_id] = {
                    "nomi": channel_name,
                    "link": channel_link,
                    "qoshilgan": datetime.now().strftime("%d.%m.%Y %H:%M"),
                }
                del admin_state[user_id]
                await message.reply_text(
                    f"""✅ <b>Kanal muvaffaqiyatli qo'shildi!</b>

📛 <b>Kanal nomi:</b> {channel_name}
🆔 <b>Kanal ID:</b> <code>{channel_id}</code>
🔗 <b>Link:</b> {channel_link}

📢 Jami kanallar: <b>{len(required_channels)}</b> ta""",
                    parse_mode="HTML"
                )
            except TelegramError as e:
                await message.reply_text(f"❌ <b>Xatolik:</b> {str(e)}\n\nBot kanalda admin qilinganmi?", parse_mode="HTML")
        except ValueError:
            await message.reply_text("❌ To'g'ri kanal ID yuboring! Masalan: <code>-1001234567890</code>", parse_mode="HTML")
        return

    # ━━━ KANAL O'CHIRISH ━━━
    if holat == "kanal_ochirish_id":
        try:
            channel_id = int(text.strip())
            if channel_id in required_channels:
                ch = required_channels[channel_id]
                keyboard = InlineKeyboardMarkup([[
                    InlineKeyboardButton("✅ Ha, o'chir", callback_data=f"confirm_delete_channel_{channel_id}"),
                    InlineKeyboardButton("❌ Bekor", callback_data="cancel_delete_channel"),
                ]])
                await message.reply_text(
                    f"""🗑️ <b>Kanalni o'chirishni tasdiqlang!</b>

📢 <b>Kanal:</b> {ch['nomi']}
🆔 <b>ID:</b> <code>{channel_id}</code>

⚠️ <b>Rostdan ham o'chirmoqchimisiz?</b>""",
                    reply_markup=keyboard,
                    parse_mode="HTML"
                )
                del admin_state[user_id]
            else:
                await message.reply_text("❌ Bu ID li kanal ro'yxatda yo'q!", parse_mode="HTML")
        except ValueError:
            await message.reply_text("❌ To'g'ri kanal ID yuboring!", parse_mode="HTML")
        return

    # ━━━ OMBOR QO'SHISH ━━━
    if holat == "ombor_qoshish":
        input_text = text.strip()
        chat_id_to_add = None
        chat_obj = None

        try:
            if input_text.startswith("https://t.me/") or input_text.startswith("@"):
                username = input_text.replace("https://t.me/", "").replace("@", "").strip().split("/")[0]
                try:
                    chat_obj = await context.bot.get_chat(f"@{username}")
                    chat_id_to_add = chat_obj.id
                except TelegramError as e:
                    await message.reply_text(
                        f"""❌ <b>Guruh topilmadi!</b>

Xatolik: {str(e)}

💡 <b>Tekshiring:</b>
   ✦ Bot guruhga admin qilinganmi?
   ✦ Link to'g'rimi?
   ✦ Guruh ochiqmi?""",
                        parse_mode="HTML"
                    )
                    return
            else:
                chat_id_to_add = int(input_text)
                try:
                    chat_obj = await context.bot.get_chat(chat_id_to_add)
                except TelegramError as e:
                    await message.reply_text(f"❌ Guruh topilmadi: {str(e)}", parse_mode="HTML")
                    return

            if chat_obj:
                grp_name = chat_obj.title or chat_obj.username or str(chat_id_to_add)
                if chat_obj.username:
                    grp_link = f"https://t.me/{chat_obj.username}"
                else:
                    grp_link = f"https://t.me/c/{str(chat_id_to_add).replace('-100', '')}"

                storage_groups[chat_id_to_add] = {
                    "nomi": grp_name,
                    "link": grp_link,
                    "qoshilgan": datetime.now().strftime("%d.%m.%Y %H:%M"),
                }
                del admin_state[user_id]

                for admin_id in list(admins_db.keys()):
                    try:
                        await context.bot.send_message(
                            admin_id,
                            f"""🎉 <b>Yangi Ombor Qo'shildi!</b>

╔══════════════════════════╗
║  🏪 <b>OMBOR TAYYOR</b> 🏪     ║
╚══════════════════════════╝

📛 <b>Guruh:</b> {grp_name}
🆔 <b>ID:</b> <code>{chat_id_to_add}</code>
🔗 <b>Link:</b> {grp_link}

✅ Bot bu guruhdan kinolarni
   foydalanuvchilarga yuboradi!

🏪 Jami ombor: <b>{len(storage_groups)}</b> ta""",
                            parse_mode="HTML"
                        )
                    except Exception:
                        pass

        except ValueError:
            await message.reply_text(
                "❌ Noto'g'ri format!\n\nLink yoki ID yuboring:\n<code>https://t.me/guruhim</code>\nyoki <code>-1001234567890</code>",
                parse_mode="HTML"
            )
        return

    # ━━━ DATABASE IMPORT ━━━
    if holat == "db_import_kutish":
        if message.document:
            doc = message.document
            if not doc.file_name.endswith(".json"):
                await message.reply_text(
                    "❌ <b>Faqat .json fayl qabul qilinadi!</b>\n\nBoshqa fayl yubormang.",
                    parse_mode="HTML"
                )
                return

            try:
                file = await context.bot.get_file(doc.file_id)
                file_bytes = await file.download_as_bytearray()
                json_str = file_bytes.decode("utf-8")
                data = json.loads(json_str)

                kinolar_q, foydalanuvchilar_q, adminlar_q, kanallar_q, ombor_q, xato, xatolar = import_database(data)

                xato_text = ""
                if xatolar:
                    xato_text = "\n\n⚠️ <b>Xatolar:</b>\n" + "\n".join(xatolar[:10])
                    if len(xatolar) > 10:
                        xato_text += f"\n...va yana {len(xatolar)-10} ta xato"

                del admin_state[user_id]

                await message.reply_text(
                    f"""✅ <b>Database Import Natijasi</b>

╔══════════════════════════╗
║  📥 <b>IMPORT YAKUNLANDI</b>   ║
╚══════════════════════════╝

📊 <b>Natijalar:</b>
🎬 <b>Kinolar:</b> +{kinolar_q} ta yangi
👥 <b>Foydalanuvchilar:</b> +{foydalanuvchilar_q} ta yangi
👑 <b>Adminlar:</b> +{adminlar_q} ta yangi
📢 <b>Kanallar:</b> +{kanallar_q} ta yangi
🏪 <b>Ombor guruhlar:</b> +{ombor_q} ta yangi
❌ <b>Xatolik:</b> {xato} ta

━━━━━━━━━━━━━━━━━━━━━━━━
📊 <b>Hozir bazada jami:</b>
🎬 Kinolar: {len(movies_db)} ta
👥 Foydalanuvchilar: {len(users_db)} ta{xato_text}""",
                    parse_mode="HTML"
                )
            except json.JSONDecodeError:
                await message.reply_text("❌ <b>JSON fayl buzilgan!</b>\n\nTo'g'ri fayl yuboring.", parse_mode="HTML")
            except Exception as e:
                await message.reply_text(f"❌ <b>Xatolik:</b> {str(e)}", parse_mode="HTML")
        else:
            await message.reply_text(
                "❌ <b>Fayl yuborilmadi!</b>\n\n📎 JSON faylni yuboring yoki /cancel bosing.",
                parse_mode="HTML"
            )
        return

    # ━━━ REKLAMA YUBORISH ━━━
    if holat == "reklama_kutish":
        del admin_state[user_id]
        sent_count = 0
        failed_count = 0
        blocked_count = 0

        await message.reply_text(
            f"""📣 <b>Reklama yuborilmoqda...</b>

⏳ Jami foydalanuvchilar: <b>{len(users_db)}</b> ta
Iltimos kuting...""",
            parse_mode="HTML"
        )

        for uid, uinfo in list(users_db.items()):
            if uid in blocked_users:
                continue
            try:
                await context.bot.copy_message(
                    chat_id=uid,
                    from_chat_id=message.chat_id,
                    message_id=message.message_id,
                )
                sent_count += 1
                await asyncio.sleep(0.05)
            except Forbidden:
                blocked_count += 1
                stats["botni_bloklaganlar"].add(uid)
                if uid in users_db:
                    users_db[uid]["faol"] = False
            except TelegramError:
                failed_count += 1

        await message.reply_text(
            f"""✅ <b>Reklama yuborildi!</b>

╔══════════════════════════╗
║  📊 <b>NATIJALAR</b> 📊        ║
╚══════════════════════════╝

✅ <b>Muvaffaqiyatli:</b> {sent_count} ta
🚫 <b>Bot bloklagan:</b> {blocked_count} ta
❌ <b>Xatolik:</b> {failed_count} ta

━━━━━━━━━━━━━━━━━━━━━━━━
📈 <i>Jami: {sent_count + blocked_count + failed_count} ta urinish</i>""",
            parse_mode="HTML"
        )
        return

    # ━━━ FOYDALANUVCHI BLOKLASH ━━━
    if holat == "bloklash_id":
        try:
            target_id = int(text.strip())
            if target_id == user_id:
                await message.reply_text("❌ O'zingizni bloklashingiz mumkin emas!")
                return
            if target_id == DEVELOPER_ID:
                await message.reply_text("❌ Super-egani bloklashingiz mumkin emas!")
                return
            if is_admin(target_id):
                await message.reply_text("❌ Adminni bloklashingiz mumkin emas!")
                return
            user_info = users_db.get(target_id, {"ism": "Noma'lum", "username": "Yo'q"})
            keyboard = InlineKeyboardMarkup([[
                InlineKeyboardButton("✅ Ha, blokla", callback_data=f"confirm_block_user_{target_id}"),
                InlineKeyboardButton("❌ Bekor", callback_data="cancel_block_user"),
            ]])
            await message.reply_text(
                f"""🚫 <b>Bloklashni tasdiqlang!</b>

👤 <b>ID:</b> <code>{target_id}</code>
👤 <b>Ism:</b> {user_info.get('ism', "Noma'lum")}
📱 <b>Username:</b> {user_info.get('username', "Yo'q")}

⚠️ <b>Rostdan ham bloklashni xohlaysizmi?</b>""",
                reply_markup=keyboard,
                parse_mode="HTML"
            )
            del admin_state[user_id]
        except ValueError:
            await message.reply_text("❌ To'g'ri Telegram ID yuboring!", parse_mode="HTML")
        return

    # ━━━ BLOKNI OCHISH ━━━
    if holat == "blok_ochish_id":
        try:
            target_id = int(text.strip())
            if target_id in blocked_users:
                del blocked_users[target_id]
                del admin_state[user_id]
                user_info = users_db.get(target_id, {"ism": "Noma'lum"})
                await message.reply_text(
                    f"""✅ <b>Blok muvaffaqiyatli ochildi!</b>

👤 <b>ID:</b> <code>{target_id}</code>
👤 <b>Ism:</b> {user_info.get('ism', "Noma'lum")}

🔓 Foydalanuvchi endi botdan foydalana oladi!""",
                    parse_mode="HTML"
                )
                try:
                    await context.bot.send_message(
                        target_id,
                        """🎉 <b>Blokilganingiz ochildi!</b>

✅ Adminlar sizning blokingizni ochdi.
Endi botdan to'liq foydalana olasiz!

🎬 Kino raqamini yuboring va tomosha qiling!""",
                        parse_mode="HTML"
                    )
                except Exception:
                    pass
            else:
                await message.reply_text(
                    f"❌ <code>{target_id}</code> ID li foydalanuvchi bloklangan ro'yxatda yo'q!",
                    parse_mode="HTML"
                )
        except ValueError:
            await message.reply_text("❌ To'g'ri Telegram ID yuboring!", parse_mode="HTML")
        return

    # ━━━ ADMIN QO'SHISH ━━━
    if holat == "admin_qoshish_id":
        try:
            new_admin_id = int(text.strip())
            if new_admin_id in admins_db:
                await message.reply_text(f"⚠️ <code>{new_admin_id}</code> allaqachon admin!", parse_mode="HTML")
                del admin_state[user_id]
                return

            admin_info = users_db.get(new_admin_id, {"ism": "Noma'lum"})
            admins_db[new_admin_id] = {
                "ism": admin_info.get("ism", "Noma'lum"),
                "qoshilgan": datetime.now().strftime("%d.%m.%Y %H:%M"),
            }
            del admin_state[user_id]

            await message.reply_text(
                f"""✅ <b>Yangi admin qo'shildi!</b>

🆔 <b>ID:</b> <code>{new_admin_id}</code>
👤 <b>Ism:</b> {admin_info.get('ism', "Noma'lum")}

👑 Jami adminlar: <b>{len(admins_db)}</b> ta""",
                parse_mode="HTML"
            )
            try:
                await context.bot.send_message(
                    new_admin_id,
                    f"""👑 <b>Siz admin qilindingiz!</b>

🎉 Tabriklaymiz! Siz @{BOT_USERNAME} botining
admini qilindingiz.

Bot panelini ochish uchun /start bosing!""",
                    parse_mode="HTML"
                )
            except Exception:
                pass
        except ValueError:
            await message.reply_text("❌ To'g'ri Telegram ID yuboring!", parse_mode="HTML")
        return

    # ━━━ USER XABAR YUBORISH ━━━
    if holat == "user_xabar_yuborish":
        del admin_state[user_id]

        await message.reply_text(
            SUGGEST_SENT_TEXT.format(ism=user.first_name),
            parse_mode="HTML"
        )

        user_info = users_db.get(user_id, {"ism": "Noma'lum", "username": "Yo'q"})
        kimdan_text = f"""💬 <b>Yangi Xabar!</b>

╔══════════════════════════╗
║  📨 <b>FOYDALANUVCHI XABARI</b> ║
╚══════════════════════════╝

👤 <b>Kimdan:</b> {user_info.get('ism', "Noma'lum")}
📱 <b>Username:</b> {user_info.get('username', "Yo'q")}
🆔 <b>User ID:</b> <code>{user_id}</code>
📅 <b>Vaqt:</b> {datetime.now().strftime("%d.%m.%Y %H:%M")}

━━━━━━━━━━━━━━━━━━━━━━━━
📝 <b>Xabar matni quyida:</b>"""

        for admin_id in list(admins_db.keys()):
            try:
                await context.bot.send_message(admin_id, kimdan_text, parse_mode="HTML")
                await context.bot.copy_message(
                    chat_id=admin_id,
                    from_chat_id=message.chat_id,
                    message_id=message.message_id,
                )
            except Exception:
                pass
        return

async def remove_admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Faqat super-ega ishlatishi mumkin: /removeadmin [ID]"""
    user_id = update.effective_user.id
    if not is_super_owner(user_id):
        await update.message.reply_text("❌ Bu buyruq faqat super-ega uchun!")
        return

    if not context.args:
        await update.message.reply_text(
            """👑 <b>Admin O'chirish</b>

Ishlatilishi: <code>/removeadmin [ID]</code>

Misol: <code>/removeadmin 123456789</code>

📋 <b>Hozirgi adminlar:</b>""" +
            "\n".join([
                f"   {'🔒 SUPER-EGA' if aid == DEVELOPER_ID else '🔑'} <code>{aid}</code> — {ainfo['ism']}"
                for aid, ainfo in admins_db.items()
            ]),
            parse_mode="HTML"
        )
        return

    try:
        target_id = int(context.args[0])
        if target_id == DEVELOPER_ID:
            await update.message.reply_text("❌ Super-egani adminlikdan chiqarib bo'lmaydi!")
            return
        if target_id not in admins_db:
            await update.message.reply_text(f"❌ <code>{target_id}</code> admin ro'yxatida yo'q!", parse_mode="HTML")
            return

        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("✅ Ha, o'chir", callback_data=f"confirm_remove_admin_{target_id}"),
            InlineKeyboardButton("❌ Bekor", callback_data="cancel_remove_admin"),
        ]])
        await update.message.reply_text(
            f"""👑 <b>Admin O'chirishni tasdiqlang!</b>

🆔 <b>ID:</b> <code>{target_id}</code>
👤 <b>Ism:</b> {admins_db[target_id]['ism']}

⚠️ <b>Rostdan ham adminlikdan chiqarmoqchimisiz?</b>""",
            reply_markup=keyboard,
            parse_mode="HTML"
        )
    except ValueError:
        await update.message.reply_text("❌ To'g'ri ID kiriting! Masalan: <code>/removeadmin 123456789</code>", parse_mode="HTML")

async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in admin_state:
        del admin_state[user_id]
        await update.message.reply_text(
            """❌ <b>Bekor qilindi!</b>

Joriy amal bekor qilindi.
Asosiy menyu ko'rsatilmoqda...""",
            reply_markup=get_main_keyboard(user_id),
            parse_mode="HTML"
        )
    else:
        await update.message.reply_text(
            "ℹ️ Bekor qilinadigan amal yo'q.",
            reply_markup=get_main_keyboard(user_id),
            parse_mode="HTML"
        )

async def handle_chat_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    my_chat_member = update.my_chat_member
    if not my_chat_member:
        return

    chat = my_chat_member.chat
    new_status = my_chat_member.new_chat_member.status
    old_status = my_chat_member.old_chat_member.status

    if chat.type not in ["channel", "supergroup", "group"]:
        return

    channel_id = chat.id

    if new_status in ["administrator"] and old_status not in ["administrator"]:
        if chat.username:
            channel_link = f"https://t.me/{chat.username}"
        else:
            channel_link = f"https://t.me/c/{str(channel_id).replace('-100', '')}"

        ch_name = chat.title or str(channel_id)

        if chat.type == "channel" and channel_id not in required_channels:
            required_channels[channel_id] = {
                "nomi": ch_name,
                "link": channel_link,
                "qoshilgan": datetime.now().strftime("%d.%m.%Y %H:%M"),
            }

        if channel_id not in storage_groups:
            storage_groups[channel_id] = {
                "nomi": ch_name,
                "link": channel_link,
                "qoshilgan": datetime.now().strftime("%d.%m.%Y %H:%M"),
            }

        for admin_id in list(admins_db.keys()):
            try:
                await context.bot.send_message(
                    admin_id,
                    f"""🎉 <b>Avtomatik Qo'shildi!</b>

╔══════════════════════════╗
║  🤖 <b>BOT ADMIN QILINDI</b>   ║
╚══════════════════════════╝

📛 <b>Guruh/Kanal:</b> {ch_name}
🆔 <b>ID:</b> <code>{channel_id}</code>
🔗 <b>Link:</b> {channel_link}
📋 <b>Tur:</b> {chat.type}

{"✅ Majburiy kanalga ham qo'shildi!" if chat.type == "channel" else ""}
✅ Ombor guruhiga qo'shildi!

🏪 Jami ombor: <b>{len(storage_groups)}</b> ta
📢 Jami kanallar: <b>{len(required_channels)}</b> ta""",
                    parse_mode="HTML"
                )
            except Exception:
                pass

    elif new_status in ["member", "left", "kicked", "restricted"] and old_status == "administrator":
        removed_info = []

        if channel_id in required_channels:
            ch_name = required_channels[channel_id]["nomi"]
            del required_channels[channel_id]
            removed_info.append(f"📢 Majburiy kanaldan o'chirildi: {ch_name}")

        if channel_id in storage_groups:
            grp_name = storage_groups[channel_id]["nomi"]
            del storage_groups[channel_id]
            removed_info.append(f"🏪 Ombor guruhidan o'chirildi: {grp_name}")

        if removed_info:
            for admin_id in list(admins_db.keys()):
                try:
                    await context.bot.send_message(
                        admin_id,
                        f"""⚠️ <b>Avtomatik O'chirildi!</b>

Bot adminlikdan olindi:
🆔 <b>ID:</b> <code>{channel_id}</code>

{"  ".join(removed_info)}

📢 Qolgan kanallar: <b>{len(required_channels)}</b> ta
🏪 Qolgan ombor: <b>{len(storage_groups)}</b> ta""",
                        parse_mode="HTML"
                    )
                except Exception:
                    pass

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 🚀 BOTNI ISHGA TUSHIRISH
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def main():
    logger.warning("🎬 Tomosha Vaqti Bot v3.0 ishga tushmoqda...")

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("cancel", cancel_command))
    app.add_handler(CommandHandler("removeadmin", remove_admin_command))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(
        filters.ChatType.PRIVATE & (
            filters.TEXT |
            filters.VIDEO |
            filters.Document.ALL |
            filters.PHOTO |
            filters.AUDIO |
            filters.VOICE |
            filters.VIDEO_NOTE
        ),
        handle_message
    ))

    from telegram.ext import ChatMemberHandler
    app.add_handler(ChatMemberHandler(handle_chat_member, ChatMemberHandler.MY_CHAT_MEMBER))

    job_queue = app.job_queue
    job_queue.run_repeating(
        daily_broadcast,
        interval=3600,
        first=10,
        name="daily_broadcast"
    )

    logger.warning(f"✅ Bot ishga tushdi! @{BOT_USERNAME}")

    app.run_polling(
        drop_pending_updates=True,
        allowed_updates=["message", "callback_query", "my_chat_member"]
    )

if __name__ == "__main__":
    main()
