import asyncio
import json
import os
import re
import time
from datetime import datetime
from pyrogram import Client, filters
from pyrogram.types import Message

# ---------------------------------------------------------
# ۱. ساختار کامل تنظیمات دائمی (Persistent Config)
# ---------------------------------------------------------
CONFIG_FILE = "config.json"

DEFAULT_CONFIG = {
    "self_active": True,
    # فونت‌ها و اسم/بیو زمان‌دار
    "clock_name": False,
    "clock_bio": False,
    "clock_style": 1,
    "custom_name": "momo",
    "custom_bio": "Selfbot Active",
    # امکانات عمومی سلف
    "afk": False,
    "afk_reason": "",
    "antidel": False,
    "antiedit": False,
    "autoloop": False,
    "autoloop_text": "",
    "autoloop_target": 0,
    "autoloop_interval": 10,
    # بازی‌ها و سرگرمی
    "dice": False,
    "slot": False,
    "basket": False,
    "bowl": False,
    "delay": 0.25,
    # اختصاصی بازی Meowie
    "auto_rescue": True,
    "auto_fish_action": "sell",   # sell, feed, fridge, off
    "auto_fish_cmd": False,       # وضعیت ارسال ماهیگیری
    "auto_fish_target_chat": 0,   # چت آیدی هدف
    "auto_fish_interval": 1800,   # فاصله زمانی ارسال (به ثانیه)
    "auto_fish_stop_time": 0      # زمان پایان (تایم‌استمپ)
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
# ۳. تایمرهای پس‌زمینه (ساعت نام/بیو و ارسال ماهیگیری)
# ---------------------------------------------------------
FONTS = {
    1: {'0':'۰','1':'۱','2':'۲','3':'۳','4':'۴','5':'۵','6':'۶','7':'۷','8':'۸','9':'۹'},
    2: {'0':'0️⃣','1':'1️⃣','2':'2️⃣','3':'3️⃣','4':'4️⃣','5':'5️⃣','6':'6️⃣','7':'7️⃣','8':'8️⃣','9':'9️⃣'}
}

def get_styled_time(style_id=1):
    now = datetime.now().strftime("%H:%M")
    font_map = FONTS.get(style_id, FONTS[1])
    return "".join(font_map.get(char, char) for char in now)

async def background_tasks():
    while True:
        try:
            if config["self_active"]:
                # ۱. بروزرسانی ساعت در نام/بیو
                current_time_str = get_styled_time(config["clock_style"])
                if config["clock_name"]:
                    new_name = f"{config['custom_name']} [{current_time_str}]"
                    await app.update_profile(first_name=new_name)
                if config["clock_bio"]:
                    new_bio = f"{config['custom_bio']} | {current_time_str}"
                    await app.update_profile(bio=new_bio)

            # هر ۱ دقیقه بروزرسانی ساعت
            await asyncio.sleep(60)
        except Exception as e:
            print(f"❌ خطا در تایمر ساعت: {e}")
            await asyncio.sleep(10)

async def auto_fish_loop():
    while True:
        try:
            if config["self_active"] and config["auto_fish_cmd"]:
                now = time.time()
                # بررسی منقضی شدن تایمر
                if config["auto_fish_stop_time"] > 0 and now >= config["auto_fish_stop_time"]:
                    config["auto_fish_cmd"] = False
                    config["auto_fish_stop_time"] = 0
                    save_config()
                    print("⏰ تایمر ارسال fish به پایان رسید.")
                else:
                    target = config["auto_fish_target_chat"]
                    if target != 0:
                        await app.send_message(target, "fish")
                        print(f"🎣 کلمه fish ارسال شد به چت: {target}")

            # انتظار به اندازه زمان تنظیم‌شده (حداقل ۳۰ ثانیه)
            interval = max(30, config.get("auto_fish_interval", 1800))
            await asyncio.sleep(interval)
        except Exception as e:
            print(f"❌ خطا در ارسال ماهیگیری: {e}")
            await asyncio.sleep(15)

# ---------------------------------------------------------
# ۴. پاسخگویی و عملکردهای خودکار
# ---------------------------------------------------------

# پاسخ خودکار حالت AFK
@app.on_message(~filters.me & (filters.private | filters.mentioned))
async def handle_afk(client: Client, message: Message):
    if config["self_active"] and config["afk"]:
        reason = config["afk_reason"] or "در حال حاضر پاسخگو نیستم."
        await message.reply(f"🤖 **حالت AFK فعال است**\n💬 علت: {reason}")

# ضد پاکسازی پیام
@app.on_deleted_messages()
async def handle_deleted(client: Client, messages):
    if config["self_active"] and config["antidel"]:
        for msg in messages:
            if msg.text:
                print(f"🗑 پیام پاک شده در چت {msg.chat.id}: {msg.text}")

# ضد ویرایش پیام
@app.on_edited_message(~filters.me)
async def handle_edited(client: Client, message: Message):
    if config["self_active"] and config["antiedit"]:
        print(f"✏️ پیام ویرایش شده در چت {message.chat.id}: {message.text}")

# دکمه‌های بازی Meowie (نجات گربه و صید ماهی)
@app.on_message(filters.group & ~filters.me)
async def handle_meowie_game(client: Client, message: Message):
    if not config["self_active"]:
        return

    text = message.text or message.caption or ""

    # نجات خودکار گربه
    if config["auto_rescue"] and "نجات پیشی خیابونی" in text:
        if message.reply_markup and message.reply_markup.inline_keyboard:
            for row in message.reply_markup.inline_keyboard:
                for btn in row:
                    if "نجات" in btn.text or "کمک" in btn.text:
                        try:
                            await message.click(btn.text)
                            print("✅ نجات گربه انجام شد.")
                        except Exception as e:
                            print(f"❌ خطا در نجات گربه: {e}")

    # اقدام خودکار ماهی صیدشده
    fish_action = config["auto_fish_action"]
    if fish_action != "off" and "شما با موفقیت" in text and "گرفتید" in text:
        if message.reply_markup and message.reply_markup.inline_keyboard:
            target_key = ""
            if fish_action == "sell": target_key = "فروش ماهی"
            elif fish_action == "feed": target_key = "بده پیشی بخوره"
            elif fish_action == "fridge": target_key = "بندازش تو یخچال"

            if target_key:
                for row in message.reply_markup.inline_keyboard:
                    for btn in row:
                        if target_key in btn.text:
                            try:
                                await message.click(btn.text)
                                print(f"✅ اقدام ماهیگیری انجام شد: {btn.text}")
                            except Exception as e:
                                print(f"❌ خطا در کلیک ماهی: {e}")

# ---------------------------------------------------------
# ۵. دستورات مدیریتی کامل (فقط از Saved Messages)
# ---------------------------------------------------------
def is_saved_messages(client: Client, message: Message):
    return message.from_user and message.from_user.is_self and message.chat.id == message.from_user.id

@app.on_message(filters.me & filters.command("panel", prefixes="."))
async def show_panel(client: Client, message: Message):
    if not is_saved_messages(client, message):
        return

    status_self = "🟢" if config["self_active"] else "🔴"
    status_rescue = "🟢" if config["auto_rescue"] else "🔴"
    status_fish_cmd = "🟢" if config["auto_fish_cmd"] else "🔴"
    status_clock_name = "🟢" if config["clock_name"] else "🔴"
    status_clock_bio = "🟢" if config["clock_bio"] else "🔴"
    status_afk = "🟢" if config["afk"] else "🔴"
    status_antidel = "🟢" if config["antidel"] else "🔴"
    status_antiedit = "🟢" if config["antiedit"] else "🔴"

    fish_modes = {"sell": "🟡 فروش", "feed": "🍖 خوراک", "fridge": "❄️ یخچال", "off": "🔴 خاموش"}
    status_fish = fish_modes.get(config["auto_fish_action"], "🔴")

    panel_text = f"""
📋 **داشبورد سلف‌بات اختصاصی momo (Saved Messages)**

━━━━━━━ Status ━━━━━━━
🤖 وضعیت سلف: {status_self}
🐱 نجات گربه خودکار: {status_rescue}
🎣 ارسال خودکار fish: {status_fish_cmd}
🐟 اقدام ماهیگیری: {status_fish}
🕒 ساعت اسم / بیو: {status_clock_name} / {status_clock_bio}
💤 حالت AFK: {status_afk}
🗑 ضد دلیت / ویرایش: {status_antidel} / {status_antiedit}
───────────────────────
━━━━━━━ Commands ━━━━━━━

🐱 **تنظیمات بازی Meowie:**
▫️ `.autorescue on/off` ➔ نجات خودکار گربه
▫️ `.autofishcmd on <چت_آیدی> <زمان_ارسال> [زمان_پایان]`
  └ مثال ۱ (هر ۳۰ دقیقه ارسال کن بدون زمان پایان):
     `.autofishcmd on -100123456789 30m`
  └ مثال ۲ (هر ۱ ساعت ارسال کن، تا ۴ ساعت آینده):
     `.autofishcmd on -100123456789 1h 4h`
▫️ `.autofishcmd off` ➔ خاموش کردن ارسال ماهیگیری
▫️ `.autofish [sell/feed/fridge/off]` ➔ اقدام ماهی صیدشده

⚙️ **ساعت و پروفایل:**
▫️ `.clockname on/off` ➔ ساعت روی اسم
▫️ `.clockbio on/off` ➔ ساعت روی بیو
▫️ `.clockstyle 1/2` ➔ تغییر فونت ساعت

🛡 **امکانات امنیتی و عمومی:**
▫️ `.afk on [علت] / .afk off` ➔ حالت غیبت
▫️ `.antidel on/off` ➔ ضد پاکسازی پیام
▫️ `.antiedit on/off` ➔ ضد ویرایش پیام
▫️ `.self on/off` ➔ خاموش/روشن سلف‌بات
▫️ `.ping` ➔ بررسی سرعت
"""
    await message.edit(panel_text)

# دستور تنظیم ارسال ماهیگیری خودکار
@app.on_message(filters.me & filters.command("autofishcmd", prefixes="."))
async def toggle_auto_fish_cmd(client: Client, message: Message):
    if not is_saved_messages(client, message):
        return

    args = message.text.split()
    if len(args) > 1:
        opt = args[1].lower()
        if opt == "on":
            if len(args) >= 4:
                try:
                    target_chat = int(args[2])
                    interval_str = args[3].lower()

                    # تبدیل زمان فاصله ارسال (مثلا 30m یا 1h)
                    if interval_str.endswith("m"):
                        interval_sec = int(interval_str.replace("m", "")) * 60
                    elif interval_str.endswith("h"):
                        interval_sec = int(interval_str.replace("h", "")) * 3600
                    else:
                        interval_sec = int(interval_str)

                    config["auto_fish_cmd"] = True
                    config["auto_fish_target_chat"] = target_chat
                    config["auto_fish_interval"] = interval_sec

                    # زمان پایان (اختیاری)
                    if len(args) >= 5:
                        stop_str = args[4].lower()
                        if stop_str.endswith("h"):
                            stop_sec = int(stop_str.replace("h", "")) * 3600
                        elif stop_str.endswith("m"):
                            stop_sec = int(stop_str.replace("m", "")) * 60
                        else:
                            stop_sec = int(stop_str) * 3600
                        config["auto_fish_stop_time"] = time.time() + stop_sec
                        stop_text = f"تا {stop_str} آینده"
                    else:
                        config["auto_fish_stop_time"] = 0
                        stop_text = "بدون محدودیت زمانی"

                    save_config()
                    await message.edit(
                        f"✅ ارسال خودکار `fish` فعال شد!\n"
                        f"🎯 چت هدف: `{target_chat}`\n"
                        f"⏱ هر `{interval_str}` یکبار\n"
                        f"⏳ مدت زمان فعالیت: {stop_text}"
                    )
                    # ارسال تست اول
                    await client.send_message(target_chat, "fish")
                except Exception as e:
                    await message.edit("❌ فرمت دستور اشتباه است!\nمثال:\n`.autofishcmd on -100123456789 30m 4h`")
            else:
                await message.edit("❌ لطفاً آیدی چت و فاصله زمانی را وارد کنید!\nمثال:\n`.autofishcmd on -100123456789 30m`")

        elif opt == "off":
            config["auto_fish_cmd"] = False
            config["auto_fish_stop_time"] = 0
            save_config()
            await message.edit("❌ ارسال خودکار `fish` غیرفعال شد.")

# دستور اقدام روی ماهی صیدشده
@app.on_message(filters.me & filters.command("autofish", prefixes="."))
async def set_auto_fish(client: Client, message: Message):
    if not is_saved_messages(client, message): return
    args = message.text.split()
    if len(args) > 1:
        opt = args[1].lower()
        if opt in ["sell", "feed", "fridge", "off"]:
            config["auto_fish_action"] = opt
            save_config()
            await message.edit(f"✅ اقدام ماهیگیری روی **{opt}** تنظیم شد.")

# نجات گربه
@app.on_message(filters.me & filters.command("autorescue", prefixes="."))
async def set_auto_rescue(client: Client, message: Message):
    if not is_saved_messages(client, message): return
    args = message.text.split()
    if len(args) > 1:
        opt = args[1].lower()
        config["auto_rescue"] = (opt == "on")
        save_config()
        await message.edit(f"✅ نجات خودکار گربه: **{opt.upper()}**")

# ساعت روی اسم و بیو
@app.on_message(filters.me & filters.command("clockname", prefixes="."))
async def toggle_clock_name(client: Client, message: Message):
    if not is_saved_messages(client, message): return
    args = message.text.split()
    if len(args) > 1:
        config["clock_name"] = (args[1].lower() == "on")
        save_config()
        await message.edit(f"✅ ساعت اسم: **{args[1].upper()}**")

@app.on_message(filters.me & filters.command("clockbio", prefixes="."))
async def toggle_clock_bio(client: Client, message: Message):
    if not is_saved_messages(client, message): return
    args = message.text.split()
    if len(args) > 1:
        config["clock_bio"] = (args[1].lower() == "on")
        save_config()
        await message.edit(f"✅ ساعت بیو: **{args[1].upper()}**")

# حالت غیبت (AFK)
@app.on_message(filters.me & filters.command("afk", prefixes="."))
async def toggle_afk(client: Client, message: Message):
    if not is_saved_messages(client, message): return
    args = message.text.split(maxsplit=2)
    if len(args) > 1:
        opt = args[1].lower()
        if opt == "on":
            config["afk"] = True
            config["afk_reason"] = args[2] if len(args) > 2 else ""
            await message.edit("✅ حالت AFK فعال شد.")
        elif opt == "off":
            config["afk"] = False
            await message.edit("❌ حالت AFK غیرفعال شد.")
        save_config()

# ضد دلیت و ضد ادیت
@app.on_message(filters.me & filters.command("antidel", prefixes="."))
async def toggle_antidel(client: Client, message: Message):
    if not is_saved_messages(client, message): return
    args = message.text.split()
    if len(args) > 1:
        config["antidel"] = (args[1].lower() == "on")
        save_config()
        await message.edit(f"✅ ضد پاکسازی: **{args[1].upper()}**")

@app.on_message(filters.me & filters.command("antiedit", prefixes="."))
async def toggle_antiedit(client: Client, message: Message):
    if not is_saved_messages(client, message): return
    args = message.text.split()
    if len(args) > 1:
        config["antiedit"] = (args[1].lower() == "on")
        save_config()
        await message.edit(f"✅ ضد ویرایش: **{args[1].upper()}**")

# پینگ و سویچ اصلی
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
        await message.edit(f"🤖 وضعیت سلف: **{args[1].upper()}**")

# ---------------------------------------------------------
# ۶. اجرای برنامه
# ---------------------------------------------------------
if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.create_task(background_tasks())
    loop.create_task(auto_fish_loop())
    print("Momo Selfbot Ready...")
    app.run()
