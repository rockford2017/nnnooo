import asyncio
import json
import os
import re
import time
from datetime import datetime
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.enums import ChatType
from pyrogram.errors import FloodWait, RPCError

# ---------------------------------------------------------
# ۱. ذخیره‌سازی پایدار تنظیمات (Persistent Config)
# ---------------------------------------------------------
CONFIG_FILE = "config.json"

DEFAULT_CONFIG = {
    "self_active": True,
    # ساعت و پروفایل
    "clock_name": False,
    "clock_style": 1,
    "custom_name": "",
    # غیبت و امنیت (حالت‌های ممکن: "off", "pv", "gp", "all")
    "afk": False,
    "afk_reason": "",
    "antidel": "off",
    "antiedit": "off",
    # تگ‌ها و لاگ‌ها
    "tag_logs": [],
    "tag_looping": False,
    "delay": 0.25,
    # اسپم و لوپ
    "loop_active": False,
    "loop_chat": 0,
    "loop_interval": 10,
    "loop_text": "",
    # بازی Meowie
    "auto_rescue": True,
    "auto_fish_enabled": True,    # سوئیچ کلی ماهیگیری
    "auto_fish_action": "sell",   # sell, feed, fridge, off
    "auto_fish_cmd": False,       # ارسال خودکار کلمه fish
    "auto_fish_target_chat": 0,   # چت هدف ماهیگیری
    "auto_fish_interval": 1800,   # فاصله ارسال (ثانیه)
    "auto_fish_stop_time": 0      # زمان پایان ارسال
}

def load_config():
    if not os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(DEFAULT_CONFIG, f, ensure_ascii=False, indent=4)
        return DEFAULT_CONFIG.copy()
    else:
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                for k, v in DEFAULT_CONFIG.items():
                    if k not in data:
                        data[k] = v
                return data
        except Exception:
            return DEFAULT_CONFIG.copy()

def save_config():
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"❌ خطا در ذخیره تنظیمات: {e}")

config = load_config()

# ---------------------------------------------------------
# ۲. ساخت کلاینت Pyrogram
# ---------------------------------------------------------
API_ID = int(os.environ.get("API_ID", 1234567))
API_HASH = os.environ.get("API_HASH", "YOUR_API_HASH")
SESSION_STRING = os.environ.get("SESSION_STRING", "")

if SESSION_STRING:
    app = Client("momo_self", api_id=API_ID, api_hash=API_HASH, session_string=SESSION_STRING)
else:
    app = Client("momo_self", api_id=API_ID, api_hash=API_HASH)

# ---------------------------------------------------------
# ۳. استایل‌های ساعت و وظایف پس‌زمینه (Background Tasks)
# ---------------------------------------------------------
FONTS = {
    1: {'0':'۰','1':'۱','2':'۲','3':'۳','4':'۴','5':'۵','6':'۶','7':'۷','8':'۸','9':'۹'},
    2: {'0':'0️⃣','1':'1️⃣','2':'2️⃣','3':'3️⃣','4':'4️⃣','5':'5️⃣','6':'6️⃣','7':'7️⃣','8':'8️⃣','9':'9️⃣'},
    3: {'0':'⓪','1':'①','2':'②','3':'③','4':'④','5':'⑤','6':'⑥','7':'⑦','8':'⑧','9':'⑨'},
    4: {'0':'0','1':'1','2':'2','3':'3','4':'4','5':'5','6':'6','7':'7','8':'8','9':'9'}
}

def get_styled_time(style_id=1):
    now = datetime.now().strftime("%H:%M")
    font_map = FONTS.get(style_id, FONTS[1])
    return "".join(font_map.get(char, char) for char in now)

async def background_clock():
    while True:
        try:
            if config["self_active"] and config["clock_name"]:
                current_time_str = get_styled_time(config["clock_style"])
                if config["custom_name"].strip():
                    new_name = f"{config['custom_name']} [{current_time_str}]"
                else:
                    new_name = f"[{current_time_str}]"
                await app.update_profile(first_name=new_name)
            await asyncio.sleep(60)
        except FloodWait as e:
            await asyncio.sleep(e.value)
        except Exception as e:
            print(f"❌ خطا در ساعت: {e}")
            await asyncio.sleep(15)

async def auto_loop_task():
    while True:
        try:
            if config["self_active"] and config["loop_active"] and config["loop_chat"] != 0 and config["loop_text"]:
                try:
                    await app.send_message(config["loop_chat"], config["loop_text"])
                except FloodWait as e:
                    await asyncio.sleep(e.value)
                except Exception as e:
                    print(f"❌ خطا در ارسال لوپ: {e}")
            interval = max(2, config.get("loop_interval", 10))
            await asyncio.sleep(interval)
        except Exception as e:
            print(f"❌ خطا در موتور اصلی ارسال تکراری: {e}")
            await asyncio.sleep(5)

async def auto_fish_loop():
    while True:
        try:
            if config["self_active"] and config["auto_fish_enabled"] and config["auto_fish_cmd"]:
                now = time.time()
                if config["auto_fish_stop_time"] > 0 and now >= config["auto_fish_stop_time"]:
                    config["auto_fish_cmd"] = False
                    config["auto_fish_stop_time"] = 0
                    save_config()
                    print("⏰ زمان ارسال خودکار fish به پایان رسید.")
                else:
                    target = config["auto_fish_target_chat"]
                    if target != 0:
                        try:
                            await app.send_message(target, "fish")
                            print(f"🎣 کلمه fish ارسال شد به چت: {target}")
                        except FloodWait as e:
                            await asyncio.sleep(e.value)
                        except Exception as e:
                            print(f"❌ خطا در ارسال دستور fish: {e}")

            interval = max(30, config.get("auto_fish_interval", 1800))
            await asyncio.sleep(interval)
        except Exception as e:
            print(f"❌ خطا در موتور ماهیگیری: {e}")
            await asyncio.sleep(15)

# ---------------------------------------------------------
# ۴. سیستم هوشمند ضد پاکسازی، ضد ویرایش و تگ‌ها
# ---------------------------------------------------------
@app.on_message(~filters.me & (filters.private | filters.mentioned))
async def handle_mentions_and_afk(client: Client, message: Message):
    if not config["self_active"]:
        return

    # ثبت لاگ تگ‌ها
    if message.mentioned:
        chat_title = message.chat.title if message.chat else "پیوی"
        sender_name = message.from_user.first_name if message.from_user else "ناشناس"
        log_entry = f"👤 {sender_name} | 💬 چت: {chat_title} | 📝 متن: {message.text or ''}"
        config["tag_logs"].append(log_entry)
        if len(config["tag_logs"]) > 50:
            config["tag_logs"].pop(0)
        save_config()

    # پاسخ AFK
    if config["afk"]:
        reason = config["afk_reason"] or "در حال حاضر آنلاین نیستم."
        await message.reply(f"🌙 **حالت AFK فعال است**\n💬 علت: {reason}")

# گزارش پیام‌های پاک‌شده
@app.on_deleted_messages()
async def handle_deleted(client: Client, messages):
    mode = config.get("antidel", "off")
    if not (config["self_active"] and mode != "off"):
        return

    for msg in messages:
        if msg and msg.text:
            is_pv = msg.chat.type == ChatType.PRIVATE if msg.chat else False
            is_group = msg.chat.type in [ChatType.GROUP, ChatType.SUPERGROUP] if msg.chat else False

            # بررسی فیلتر PV یا Group
            if (mode == "pv" and not is_pv) or (mode == "gp" and not is_group):
                continue

            chat_title = msg.chat.title if msg.chat else "پیوی"
            sender = msg.from_user.first_name if msg.from_user else "ناشناس"
            report = f"🛡 **[گزارش ضد پاکسازی - {mode.upper()}]**\n👤 **فرستنده:** {sender}\n💬 **چت:** {chat_title}\n📝 **متن پیام پاک‌شده:**\n`{msg.text}`"
            try:
                await client.send_message("me", report)
            except Exception as e:
                print(f"❌ خطا در ارسال گزارش پاکسازی: {e}")

# گزارش پیام‌های ویرایش‌شده
@app.on_edited_message(~filters.me)
async def handle_edited(client: Client, message: Message):
    mode = config.get("antiedit", "off")
    if not (config["self_active"] and mode != "off"):
        return

    if message and message.text:
        is_pv = message.chat.type == ChatType.PRIVATE
        is_group = message.chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]

        # بررسی فیلتر PV یا Group
        if (mode == "pv" and not is_pv) or (mode == "gp" and not is_group):
            return

        chat_title = message.chat.title if message.chat else "پیوی"
        sender = message.from_user.first_name if message.from_user else "ناشناس"
        report = f"✏️ **[گزارش ضد ویرایش - {mode.upper()}]**\n👤 **فرستنده:** {sender}\n💬 **چت:** {chat_title}\n📝 **متن جدید:**\n`{message.text}`"
        try:
            await client.send_message("me", report)
        except Exception as e:
            print(f"❌ خطا در ارسال گزارش ویرایش: {e}")

# کلیک خودکار دکمه‌های بازی Meowie
@app.on_message(filters.group & ~filters.me)
async def handle_meowie_game(client: Client, message: Message):
    if not config["self_active"]:
        return

    text = message.text or message.caption or ""

    # ۱. نجات گربه خیابانی
    if config["auto_rescue"] and "نجات پیشی خیابونی" in text:
        if message.reply_markup and message.reply_markup.inline_keyboard:
            for row in message.reply_markup.inline_keyboard:
                for btn in row:
                    if "نجات" in btn.text or "کمک" in btn.text:
                        try:
                            await message.click(btn.text)
                        except Exception as e:
                            print(f"❌ خطا در نجات گربه: {e}")

    # ۲. اقدام روی ماهی صیدشده
    if config["auto_fish_enabled"]:
        fish_action = config["auto_fish_action"]
        if fish_action != "off" and ("شما با موفقیت" in text or "گرفتید" in text or "ماهی" in text):
            if message.reply_markup and message.reply_markup.inline_keyboard:
                keywords = []
                if fish_action == "sell": keywords = ["فروش", "فروختن", "sell"]
                elif fish_action == "feed": keywords = ["بخور", "خوراک", "پیشی", "feed"]
                elif fish_action == "fridge": keywords = ["یخچال", "انبار", "fridge"]

                for row in message.reply_markup.inline_keyboard:
                    for btn in row:
                        if any(kw in btn.text for kw in keywords):
                            try:
                                await message.click(btn.text)
                            except Exception as e:
                                print(f"❌ خطا در کلیک ماهی: {e}")

# ---------------------------------------------------------
# ۵. دستورات منو و داشبورد اصلی (.help)
# ---------------------------------------------------------
def is_saved_messages(client: Client, message: Message):
    return message.from_user and message.from_user.is_self and message.chat.id == message.from_user.id

def format_status(mode_str):
    if mode_str == "off": return "🔴 خاموش"
    elif mode_str == "pv": return "🟢 فقط PV"
    elif mode_str == "gp": return "🟢 فقط گروه"
    else: return "🟢 همه (PV + گروه)"

@app.on_message(filters.me & filters.command("help", prefixes="."))
async def show_help(client: Client, message: Message):
    if not is_saved_messages(client, message): return

    s_self = "🟢" if config["self_active"] else "🔴"
    s_cname = "🟢" if config["clock_name"] else "🔴"
    s_afk = "🟢" if config["afk"] else "🔴"
    s_antidel = format_status(config.get("antidel", "off"))
    s_antiedit = format_status(config.get("antiedit", "off"))
    s_loop = "🟢" if config["loop_active"] else "🔴"
    s_rescue = "🟢" if config["auto_rescue"] else "🔴"
    s_fish_cmd = "🟢" if (config["auto_fish_enabled"] and config["auto_fish_cmd"]) else "🔴"

    fish_modes = {"sell": "💰 فروش", "feed": "🍖 خوراک", "fridge": "❄️ یخچال", "off": "🔴 خاموش"}
    s_fish = fish_modes.get(config["auto_fish_action"], "🔴 خاموش") if config["auto_fish_enabled"] else "🔴 خاموش"

    help_text = f"""
📋 **داشبورد سلف‌بات اختصاصی**
━━━━━━━ Status ━━━━━━━
🤖 وضعیت سلف: {s_self}
⏰ ساعت اسم: {s_cname} (فونت {config['clock_style']})
🌙 حالت AFK: {s_afk}
🛡 ضد پاکسازی: {s_antidel}
✏️ ضد ویرایش: {s_antiedit}
🔄 ارسال تکراری: {s_loop}
🏷 تگ‌های ثبت‌شده: {len(config['tag_logs'])} عدد
🐱 نجات گربه خودکار: {s_rescue}
🎣 ارسال خودکار fish: {s_fish_cmd}
🐟 اقدام ماهیگیری: {s_fish}
━━━━━━━ Commands ━━━━━━━

🏷 **تگ‌ها و گزارش‌ها:**
▫️ `.tags` ➔ مشاهده لاگ تگ‌ها
▫️ `.cleartags` ➔ پاکسازی تاریخچه تگ
▫️ `.tag [چت_آیدی] [متن]` ➔ تگ تکی اعضا
▫️ `.all [چت_آیدی] [متن]` ➔ تگ ۵ تایی اعضا
▫️ `.stoptag` ➔ توقف تگ‌زنی

🐱 **بازی Meowie:**
▫️ `.autorescue on/off` ➔ نجات گربه
▫️ `.autofish on/off` ➔ خاموش/روشن کلی ماهیگیری
▫️ `.autofishcmd on <چت_آیدی> <فاصله> [مدت]`
  └ مثال: `.autofishcmd on -1003952467253 30m 4h`
▫️ `.autofishcmd off` ➔ خاموش کردن ارسال fish
▫️ `.autofish [sell/feed/fridge/off]`

⚡️ **تنظیمات حساب:**
▫️ `.self on/off` ➔ خاموش/روشن سلف‌بات
▫️ `.clockname on/off` ➔ ساعت اسم
▫️ `.clockstyle [1-4]` ➔ تغییر استایل ساعت
▫️ `.afk on [دلیل] / .afk off` ➔ حالت غیبت
▫️ `.antidel [pv/gp/all/off]` ➔ ضد پاکسازی تفکیک‌شده
▫️ `.antiedit [pv/gp/all/off]` ➔ ضد ویرایش تفکیک‌شده

💣 **اسپم و ابزارها:**
▫️ `.spam [چت_آیدی] [تعداد] [متن]` ➔ اسپم سریع
▫️ `.delayspam [چت_آیدی] [تاخیر] [تعداد] [متن]` ➔ اسپم با تاخیر
▫️ `.loop [here/آیدی] [ثانیه] [متن]` ➔ ارسال تکراری
▫️ `.stoploop` ➔ توقف ارسال تکراری
▫️ `.del [تعداد]` ➔ پاکسازی پیام‌های خود
▫️ `.calc [عبارت]` ➔ ماشین حساب
▫️ `.type [متن]` ➔ تایپ افکتی
▫️ `.info` ➔ دریافت اطلاعات کاربر
▫️ `.ping` ➔ بررسی سرعت سلف‌بات
"""
    await message.edit(help_text.strip())

# --- دستورات هوشمند ضد پاکسازی و ضد ویرایش ---
@app.on_message(filters.me & filters.command("antidel", prefixes="."))
async def toggle_antidel(client: Client, message: Message):
    if not is_saved_messages(client, message): return
    args = message.text.split()
    if len(args) > 1:
        opt = args[1].lower()
        if opt in ["pv", "gp", "all"]:
            config["antidel"] = opt
            st = f"فعال روی ({opt.upper()})"
        elif opt == "on":
            config["antidel"] = "all"
            st = "فعال روی (ALL)"
        else:
            config["antidel"] = "off"
            st = "خاموش"
        save_config()
        await message.edit(f"🛡 **ضد پاکسازی {st} شد و ذخیره گردید!**")

@app.on_message(filters.me & filters.command("antiedit", prefixes="."))
async def toggle_antiedit(client: Client, message: Message):
    if not is_saved_messages(client, message): return
    args = message.text.split()
    if len(args) > 1:
        opt = args[1].lower()
        if opt in ["pv", "gp", "all"]:
            config["antiedit"] = opt
            st = f"فعال روی ({opt.upper()})"
        elif opt == "on":
            config["antiedit"] = "all"
            st = "فعال روی (ALL)"
        else:
            config["antiedit"] = "off"
            st = "خاموش"
        save_config()
        await message.edit(f"✏️ **ضد ویرایش {st} شد و ذخیره گردید!**")

# --- دستور ارسال تکراری (لوپ) ---
@app.on_message(filters.me & filters.command("loop", prefixes="."))
async def start_loop(client: Client, message: Message):
    if not is_saved_messages(client, message): return
    args = message.text.split(maxsplit=3)
    if len(args) < 4:
        await message.edit("❌ مثال: `.loop -1003952467253 10 متن` ")
        return

    chat_target = message.chat.id if args[1].lower() == "here" else int(args[1])
    config["loop_chat"] = chat_target
    config["loop_interval"] = int(args[2])
    config["loop_text"] = args[3]
    config["loop_active"] = True
    save_config()

    msg_reply = f"""
🔄 **ارسال تکراری فعال و ذخیره شد!**
🎯 **هدف:** `{chat_target}`
⏱ **بازه زمانی:** هر `{args[2]}` ثانیه
📝 **متن:** `{args[3]}`
"""
    await message.edit(msg_reply.strip())

@app.on_message(filters.me & filters.command("stoploop", prefixes="."))
async def stop_loop(client: Client, message: Message):
    if not is_saved_messages(client, message): return
    config["loop_active"] = False
    save_config()
    await message.edit("🛑 **ارسال تکراری متوقف و ذخیره شد!**")

# --- دستورات ماهیگیری و نجات گربه ---
@app.on_message(filters.me & filters.command("autofish", prefixes="."))
async def set_auto_fish(client: Client, message: Message):
    if not is_saved_messages(client, message): return
    args = message.text.split()
    if len(args) > 1:
        opt = args[1].lower()
        if opt == "on":
            config["auto_fish_enabled"] = True
            save_config()
            await message.edit("🎣 **سیستم ماهیگیری خودکار فعال و ذخیره شد!**")
        elif opt == "off":
            config["auto_fish_enabled"] = False
            save_config()
            await message.edit("🛑 **سیستم ماهیگیری خودکار غیرفعال و ذخیره شد!**")
        elif opt in ["sell", "feed", "fridge"]:
            config["auto_fish_action"] = opt
            config["auto_fish_enabled"] = True
            save_config()
            labels = {"sell": "فروش ماهی 💰", "feed": "بده پیشی بخوره 🍖", "fridge": "بندازش تو یخچال ❄️"}
            await message.edit(f"🐟 **تصمیم ماهیگیری روی «{labels[opt]}» تنظیم و ذخیره شد!**")

@app.on_message(filters.me & filters.command("autofishcmd", prefixes="."))
async def toggle_auto_fish_cmd(client: Client, message: Message):
    if not is_saved_messages(client, message): return
    args = message.text.split()
    if len(args) > 1:
        opt = args[1].lower()
        if opt == "on" and len(args) >= 4:
            try:
                target_chat = int(args[2])
                interval_str = args[3].lower()

                if interval_str.endswith("m"): interval_sec = int(interval_str.replace("m", "")) * 60
                elif interval_str.endswith("h"): interval_sec = int(interval_str.replace("h", "")) * 3600
                else: interval_sec = int(interval_str)

                config["auto_fish_cmd"] = True
                config["auto_fish_target_chat"] = target_chat
                config["auto_fish_interval"] = interval_sec

                dur_text = "نامحدود"
                if len(args) >= 5:
                    stop_str = args[4].lower()
                    stop_sec = int(stop_str.replace("h", "")) * 3600 if stop_str.endswith("h") else int(stop_str.replace("m", "")) * 60
                    config["auto_fish_stop_time"] = time.time() + stop_sec
                    dur_text = f"`{args[4]}`"
                else:
                    config["auto_fish_stop_time"] = 0

                save_config()

                msg_reply = f"""
🎣 **ارسال خودکار ماهیگیری (fish) فعال و ذخیره شد!**
🎯 **هدف:** `{target_chat}`
⏱ **فاصله ارسال:** `{args[3]}`
⌛️ **مدت زمان:** {dur_text}
"""
                await message.edit(msg_reply.strip())
                await client.send_message(target_chat, "fish")
            except Exception:
                await message.edit("❌ فرمت دستور اشتباه است.")
        elif opt == "off":
            config["auto_fish_cmd"] = False
            config["auto_fish_stop_time"] = 0
            save_config()
            await message.edit("🛑 **ارسال خودکار fish متوقف و ذخیره شد!**")

@app.on_message(filters.me & filters.command("autorescue", prefixes="."))
async def set_auto_rescue(client: Client, message: Message):
    if not is_saved_messages(client, message): return
    args = message.text.split()
    if len(args) > 1:
        opt = args[1].lower()
        config["auto_rescue"] = (opt == "on")
        save_config()
        st = "فعال" if config["auto_rescue"] else "غیرفعال"
        await message.edit(f"🐱 **نجات خودکار گربه {st} و ذخیره شد!**")

# --- تنظیمات عمومی و حساب ---
@app.on_message(filters.me & filters.command("clockname", prefixes="."))
async def toggle_clock_name(client: Client, message: Message):
    if not is_saved_messages(client, message): return
    args = message.text.split()
    if len(args) > 1:
        opt = args[1].lower()
        config["clock_name"] = (opt == "on")
        save_config()
        await message.edit(f"⏰ **ساعت روی اسم: {opt.upper()} و ذخیره شد!**")

@app.on_message(filters.me & filters.command("clockstyle", prefixes="."))
async def change_clock_style(client: Client, message: Message):
    if not is_saved_messages(client, message): return
    args = message.text.split()
    if len(args) > 1 and args[1].isdigit():
        config["clock_style"] = int(args[1])
        save_config()
        await message.edit(f"🎨 **استایل ساعت روی {args[1]} تنظیم و ذخیره شد!**")

@app.on_message(filters.me & filters.command("afk", prefixes="."))
async def toggle_afk(client: Client, message: Message):
    if not is_saved_messages(client, message): return
    args = message.text.split(maxsplit=2)
    if len(args) > 1:
        opt = args[1].lower()
        if opt == "on":
            config["afk"] = True
            config["afk_reason"] = args[2] if len(args) > 2 else ""
            await message.edit(f"🌙 **حالت AFK فعال و ذخیره شد!**\n💬 علت: {config['afk_reason']}")
        elif opt == "off":
            config["afk"] = False
            await message.edit("☀️ **حالت AFK غیرفعال و ذخیره شد!**")
        save_config()

# --- تگ‌زنی، اسپم و ابزارها ---
@app.on_message(filters.me & filters.command("tags", prefixes="."))
async def view_tags(client: Client, message: Message):
    if not is_saved_messages(client, message): return
    if not config["tag_logs"]:
        await message.edit("📜 هیچ تگی ثبت نشده است.")
        return
    text = "📜 **تاریخچه تگ‌های شما:**\n\n" + "\n".join(config["tag_logs"][-15:])
    await message.edit(text)

@app.on_message(filters.me & filters.command("cleartags", prefixes="."))
async def clear_tags(client: Client, message: Message):
    if not is_saved_messages(client, message): return
    config["tag_logs"] = []
    save_config()
    await message.edit("✅ تاریخچه تگ‌ها پاکسازی شد.")

@app.on_message(filters.me & filters.command("tag", prefixes="."))
async def tag_single(client: Client, message: Message):
    if not is_saved_messages(client, message): return
    args = message.text.split(maxsplit=2)
    if len(args) < 3:
        await message.edit("❌ مثال: `.tag -1003952467253 متن` ")
        return
    chat_id, tag_text = int(args[1]), args[2]
    config["tag_looping"] = True
    save_config()
    await message.edit("🏷 تگ‌زنی شروع شد...")
    async for member in client.get_chat_members(chat_id):
        if not config["tag_looping"]: break
        if not member.user.is_bot:
            await client.send_message(chat_id, f"[{member.user.first_name}](tg://user?id={member.user.id}) {tag_text}")
            await asyncio.sleep(config["delay"])

@app.on_message(filters.me & filters.command("all", prefixes="."))
async def tag_all_five(client: Client, message: Message):
    if not is_saved_messages(client, message): return
    args = message.text.split(maxsplit=2)
    if len(args) < 3:
        await message.edit("❌ مثال: `.all -1003952467253 متن` ")
        return
    chat_id, tag_text = int(args[1]), args[2]
    config["tag_looping"] = True
    save_config()
    await message.edit("🏷 تگ ۵ تایی شروع شد...")
    mentions = []
    async for member in client.get_chat_members(chat_id):
        if not config["tag_looping"]: break
        if not member.user.is_bot:
            mentions.append(f"[{member.user.first_name}](tg://user?id={member.user.id})")
            if len(mentions) == 5:
                await client.send_message(chat_id, " ".join(mentions) + " " + tag_text)
                mentions = []
                await asyncio.sleep(config["delay"])

@app.on_message(filters.me & filters.command("stoptag", prefixes="."))
async def stop_tagging(client: Client, message: Message):
    if not is_saved_messages(client, message): return
    config["tag_looping"] = False
    save_config()
    await message.edit("🛑 تگ‌زنی متوقف شد.")

@app.on_message(filters.me & filters.command("spam", prefixes="."))
async def fast_spam(client: Client, message: Message):
    if not is_saved_messages(client, message): return
    args = message.text.split(maxsplit=3)
    if len(args) < 4:
        await message.edit("❌ مثال: `.spam -1003952467253 5 متن` ")
        return
    chat_id, count, text = int(args[1]), int(args[2]), args[3]
    await message.edit("💥 اسپم شروع شد...")
    for _ in range(count):
        await client.send_message(chat_id, text)
        await asyncio.sleep(config["delay"])

@app.on_message(filters.me & filters.command("delayspam", prefixes="."))
async def delay_spam(client: Client, message: Message):
    if not is_saved_messages(client, message): return
    args = message.text.split(maxsplit=4)
    if len(args) < 5:
        await message.edit("❌ مثال: `.delayspam -1003952467253 2 5 متن` ")
        return
    chat_id, delay, count, text = int(args[1]), float(args[2]), int(args[3]), args[4]
    await message.edit("⏱ اسپم با تاخیر شروع شد...")
    for _ in range(count):
        await client.send_message(chat_id, text)
        await asyncio.sleep(delay)

@app.on_message(filters.me & filters.command("del", prefixes="."))
async def delete_messages(client: Client, message: Message):
    if not is_saved_messages(client, message): return
    args = message.text.split()
    if len(args) > 1 and args[1].isdigit():
        count = int(args[1])
        async for msg in client.get_chat_history(message.chat.id, limit=count):
            if msg.from_user and msg.from_user.is_self:
                await msg.delete()

@app.on_message(filters.me & filters.command("calc", prefixes="."))
async def calculator(client: Client, message: Message):
    if not is_saved_messages(client, message): return
    expr = message.text.split(maxsplit=1)
    if len(expr) > 1:
        try:
            res = eval(expr[1])
            await message.edit(f"🧮 نتیجه: `{res}`")
        except Exception:
            await message.edit("❌ عبارت ریاضی نامعتبر است.")

@app.on_message(filters.me & filters.command("type", prefixes="."))
async def typewriter(client: Client, message: Message):
    if not is_saved_messages(client, message): return
    text = message.text.split(maxsplit=1)
    if len(text) > 1:
        full_text = text[1]
        out = ""
        for char in full_text:
            out += char
            await message.edit(out + "▒")
            await asyncio.sleep(0.1)
        await message.edit(full_text)

@app.on_message(filters.me & filters.command("info", prefixes="."))
async def get_info(client: Client, message: Message):
    if not is_saved_messages(client, message): return
    user = message.reply_to_message.from_user if message.reply_to_message else message.from_user
    info_text = f"""
👤 **اطلاعات کاربر:**
🆔 آیدی عددی: `{user.id}`
نام: {user.first_name}
نام خانوادگی: {user.last_name or 'ندارد'}
یوزرنیم: @{user.username if user.username else 'ندارد'}
ربات: {'بله' if user.is_bot else 'خیر'}
"""
    await message.edit(info_text.strip())

@app.on_message(filters.me & filters.command("ping", prefixes="."))
async def ping_cmd(client: Client, message: Message):
    if not is_saved_messages(client, message): return
    start = time.time()
    await message.edit("🏓 Pong!")
    end = time.time()
    await message.edit(f"🏓 Pong!\n⏱ سرعت: `{round((end - start) * 1000)}ms`")

@app.on_message(filters.me & filters.command("self", prefixes="."))
async def toggle_self(client: Client, message: Message):
    if not is_saved_messages(client, message): return
    args = message.text.split()
    if len(args) > 1:
        config["self_active"] = (args[1].lower() == "on")
        save_config()
        await message.edit(f"🤖 **وضعیت سلف‌بات: {args[1].upper()} و ذخیره شد!**")

# ---------------------------------------------------------
# ۶. اجرای برنامه‌ها
# ---------------------------------------------------------
if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.create_task(background_clock())
    loop.create_task(auto_loop_task())
    loop.create_task(auto_fish_loop())
    print("Momo Selfbot Ready & Updated with PV/GP Separation...")
    app.run()
