import asyncio
import json
import os
import re
import time
from datetime import datetime
from pyrogram import Client, filters
from pyrogram.types import Message

# ---------------------------------------------------------
# ۱. ذخیره‌سازی پایداری تنظیمات (Persistent Config)
# ---------------------------------------------------------
CONFIG_FILE = "config.json"

DEFAULT_CONFIG = {
    "self_active": True,
    # ساعت و پروفایل
    "clock_name": False,
    "clock_bio": False,
    "clock_style": 1,
    "custom_name": "",
    "custom_bio": "Selfbot Active",
    # غیبت و امنیت
    "afk": False,
    "afk_reason": "",
    "antidel": False,
    "antiedit": False,
    # تگ‌ها و لاگ‌ها
    "tag_logs": [],
    "tag_looping": False,
    # بازی‌ها و تاس‌ها
    "dice": False,
    "dice_val": None,
    "slot": False,
    "slot_val": None,
    "basket": False,
    "bowl": False,
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
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=4)

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
# ۳. سیستم ساعت و پس‌زمینه
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
            if config["self_active"]:
                current_time_str = get_styled_time(config["clock_style"])
                
                # ساعت روی اسم بدون اسم گیت‌هاب / اکانت
                if config["clock_name"]:
                    if config["custom_name"].strip():
                        new_name = f"{config['custom_name']} [{current_time_str}]"
                    else:
                        new_name = f"[{current_time_str}]"
                    await app.update_profile(first_name=new_name)

                # ساعت روی بیو
                if config["clock_bio"]:
                    new_bio = f"{config['custom_bio']} | {current_time_str}"
                    await app.update_profile(bio=new_bio)

            await asyncio.sleep(60)
        except Exception as e:
            print(f"❌ خطا در ساعت: {e}")
            await asyncio.sleep(10)

async def auto_loop_task():
    while True:
        try:
            if config["self_active"] and config["loop_active"] and config["loop_chat"] != 0 and config["loop_text"]:
                await app.send_message(config["loop_chat"], config["loop_text"])
            interval = max(2, config.get("loop_interval", 10))
            await asyncio.sleep(interval)
        except Exception as e:
            print(f"❌ خطا در ارسال لوپ: {e}")
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
                        await app.send_message(target, "fish")
                        print(f"🎣 کلمه fish ارسال شد به چت: {target}")

            interval = max(30, config.get("auto_fish_interval", 1800))
            await asyncio.sleep(interval)
        except Exception as e:
            print(f"❌ خطا در اجرای ماهیگیری: {e}")
            await asyncio.sleep(15)

# ---------------------------------------------------------
# ۴. کلیک خودکار رو دکمه‌ها (نجات گربه + اقدام صید)
# ---------------------------------------------------------
@app.on_message(~filters.me & (filters.private | filters.mentioned))
async def handle_mentions_and_afk(client: Client, message: Message):
    if not config["self_active"]:
        return

    if message.mentioned:
        log_entry = f"👤 {message.from_user.first_name if message.from_user else 'ناشناس'} | 💬 چت: {message.chat.title or 'پیوی'} | 📝 متن: {message.text or ''}"
        config["tag_logs"].append(log_entry)
        if len(config["tag_logs"]) > 50:
            config["tag_logs"].pop(0)
        save_config()

    if config["afk"]:
        reason = config["afk_reason"] or "در حال حاضر آنلاین نیستم."
        await message.reply(f"🌙 **حالت AFK فعال است**\n💬 علت: {reason}")

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
                            print("🐱 دکمه نجات گربه زده شد.")
                        except Exception as e:
                            print(f"❌ خطا در نجات گربه: {e}")

    # ۲. اکشن روی ماهی صیدشده (فروش / خوراک / یخچال)
    if config["auto_fish_enabled"]:
        fish_action = config["auto_fish_action"]
        if fish_action != "off" and ("شما با موفقیت" in text or "گرفتید" in text or "ماهی" in text):
            if message.reply_markup and message.reply_markup.inline_keyboard:
                keywords = []
                if fish_action == "sell":
                    keywords = ["فروش", "فروختن", "sell"]
                elif fish_action == "feed":
                    keywords = ["بخور", "خوراک", "پیشی", "feed"]
                elif fish_action == "fridge":
                    keywords = ["یخچال", "انبار", "fridge"]

                for row in message.reply_markup.inline_keyboard:
                    for btn in row:
                        if any(kw in btn.text for kw in keywords):
                            try:
                                await message.click(btn.text)
                                print(f"🐟 روی دکمه '{btn.text}' کلیک شد.")
                            except Exception as e:
                                print(f"❌ خطا در کلیک دکمه ماهی: {e}")

# ---------------------------------------------------------
# ۵. دستورات منو و کنترل
# ---------------------------------------------------------
def is_saved_messages(client: Client, message: Message):
    return message.from_user and message.from_user.is_self and message.chat.id == message.from_user.id

@app.on_message(filters.me & filters.command("panel", prefixes="."))
async def show_panel(client: Client, message: Message):
    if not is_saved_messages(client, message): return

    s_self = "🟢" if config["self_active"] else "🔴"
    s_cname = "🟢" if config["clock_name"] else "🔴"
    s_cbio = "🟢" if config["clock_bio"] else "🔴"
    s_afk = "🟢" if config["afk"] else "🔴"
    s_antidel = "🟢" if config["antidel"] else "🔴"
    s_antiedit = "🟢" if config["antiedit"] else "🔴"
    s_loop = "🟢" if config["loop_active"] else "🔴"
    s_rescue = "🟢" if config["auto_rescue"] else "🔴"
    s_fish_cmd = "🟢" if (config["auto_fish_enabled"] and config["auto_fish_cmd"]) else "🔴"

    fish_modes = {"sell": "💰 فروش ماهی", "feed": "🍖 خوراک پیشی", "fridge": "❄️ قرار در یخچال", "off": "🔴 خاموش"}
    s_fish = fish_modes.get(config["auto_fish_action"], "🔴") if config["auto_fish_enabled"] else "🔴 خاموش"

    panel_text = f"""
📋 **داشبورد سلف‌بات اختصاصی**
━━━━━━━ Status ━━━━━━━
🤖 وضعیت سلف: {s_self}
⏰ ساعت اسم: {s_cname}
📝 ساعت بیو: {s_cbio} (فونت {config['clock_style']})
🌙 حالت AFK: {s_afk}
🛡 ضد پاکسازی: {s_antidel}
✏️ ضد ویرایش: {s_antiedit}
🔄 ارسال تکراری: {s_loop}
🐱 نجات خودکار گربه: {s_rescue}
🎣 ارسال خودکار fish: {s_fish_cmd}
🐟 تصمیم ماهی صیدشده: {s_fish}
━━━━━━━ Commands ━━━━━━━

🐱 **تنظیمات بازی Meowie:**
▫️ `.autorescue on/off`
  └ فعال/غیرفعال‌سازی نجات گربه
▫️ `.autofish on/off`
  └ روشن/خاموش کردن کل سیستم ماهیگیری
▫️ `.autofish [sell/feed/fridge/off]`
  └ تعیین اقدام روی ماهی صیدشده
▫️ `.autofishcmd on <چت_آیدی> <فاصله> [مدت]`
  └ شروع ارسال خودکار `fish`
▫️ `.autofishcmd off`

🔄 **ارسال تکراری (لوپ):**
▫️ `.loop [here/چت_آیدی] [ثانیه] [متن]`
▫️ `.stoploop`

⚡️ **تنظیمات حساب و پروفایل:**
▫️ `.clockname on/off` ➔ ساعت اسم
▫️ `.clockbio on/off` ➔ ساعت بیوگرافی
▫️ `.clockstyle [1-4]` ➔ فونت ساعت
▫️ `.afk on [دلیل] / .afk off` ➔ حالت غیبت
▫️ `.antidel on/off` ➔ ضد پاکسازی
▫️ `.antiedit on/off` ➔ ضد ویرایش
▫️ `.self on/off` ➔ خاموش/روشن سلف
"""
    await message.edit(panel_text)

# --- دستور تنظیم اقدام ماهی صیدشده ---
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

# --- دستور ارسال خودکار کلمه fish ---
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

# --- دستور نجات خودکار گربه ---
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

# --- سایر دستورات ---
@app.on_message(filters.me & filters.command("clockname", prefixes="."))
async def toggle_clock_name(client: Client, message: Message):
    if not is_saved_messages(client, message): return
    args = message.text.split()
    if len(args) > 1:
        opt = args[1].lower()
        config["clock_name"] = (opt == "on")
        save_config()
        await message.edit(f"⏰ **ساعت روی اسم: {opt.upper()} و ذخیره شد!**")

@app.on_message(filters.me & filters.command("clockbio", prefixes="."))
async def toggle_clock_bio(client: Client, message: Message):
    if not is_saved_messages(client, message): return
    args = message.text.split()
    if len(args) > 1:
        opt = args[1].lower()
        config["clock_bio"] = (opt == "on")
        save_config()
        await message.edit(f"📝 **ساعت روی بیو: {opt.upper()} و ذخیره شد!**")

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

@app.on_message(filters.me & filters.command("clockstyle", prefixes="."))
async def change_clock_style(client: Client, message: Message):
    if not is_saved_messages(client, message): return
    args = message.text.split()
    if len(args) > 1 and args[1].isdigit():
        config["clock_style"] = int(args[1])
        save_config()
        await message.edit(f"🎨 **استایل ساعت روی {args[1]} تنظیم و ذخیره شد!**")

@app.on_message(filters.me & filters.command("antidel", prefixes="."))
async def toggle_antidel(client: Client, message: Message):
    if not is_saved_messages(client, message): return
    args = message.text.split()
    if len(args) > 1:
        config["antidel"] = (args[1].lower() == "on")
        save_config()
        await message.edit(f"🛡 **ضد پاکسازی: {args[1].upper()} و ذخیره شد!**")

@app.on_message(filters.me & filters.command("antiedit", prefixes="."))
async def toggle_antiedit(client: Client, message: Message):
    if not is_saved_messages(client, message): return
    args = message.text.split()
    if len(args) > 1:
        config["antiedit"] = (args[1].lower() == "on")
        save_config()
        await message.edit(f"✏️ **ضد ویرایش: {args[1].upper()} و ذخیره شد!**")

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
    print("Momo Selfbot Ready & Fully Updated...")
    app.run()
