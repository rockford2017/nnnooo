import asyncio
import json
import os
import re
import time
from datetime import datetime
from pyrogram import Client, filters
from pyrogram.types import Message

# ---------------------------------------------------------
# ۱. ساختار جامع تنظیمات و ذخیره‌سازی پایداری (config.json)
# ---------------------------------------------------------
CONFIG_FILE = "config.json"

DEFAULT_CONFIG = {
    "self_active": True,
    # ساعت و پروفایل
    "clock_name": False,
    "clock_bio": False,
    "clock_style": 1,
    "custom_name": "momo",
    "custom_bio": "Selfbot Active",
    # غیبت و امنیت
    "afk": False,
    "afk_reason": "",
    "antidel": False,
    "antiedit": False,
    # تگ‌ها و گزارش‌ها
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
    # اسپم و ارسال تکراری
    "loop_active": False,
    "loop_chat": 0,
    "loop_interval": 10,
    "loop_text": "",
    # بازی Meowie
    "auto_rescue": True,
    "auto_fish_action": "sell",   # sell, feed, fridge, off
    "auto_fish_cmd": False,       # ارسال خودکار کلمه fish
    "auto_fish_target_chat": 0,   # چت هدف ماهیگیری
    "auto_fish_interval": 1800,   # فاصله ارسال
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
# ۳. سیستم ساعت، استایل‌ها و تایمرهای پس‌زمینه
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
                if config["clock_name"]:
                    await app.update_profile(first_name=f"{config['custom_name']} [{current_time_str}]")
                if config["clock_bio"]:
                    await app.update_profile(bio=f"{config['custom_bio']} | {current_time_str}")
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
            if config["self_active"] and config["auto_fish_cmd"]:
                now = time.time()
                if config["auto_fish_stop_time"] > 0 and now >= config["auto_fish_stop_time"]:
                    config["auto_fish_cmd"] = False
                    config["auto_fish_stop_time"] = 0
                    save_config()
                    print("⏰ زمان ارسال خودکار fish تمام شد.")
                else:
                    target = config["auto_fish_target_chat"]
                    if target != 0:
                        await app.send_message(target, "fish")
                        print(f"🎣 کلمه fish ارسال شد به: {target}")

            interval = max(30, config.get("auto_fish_interval", 1800))
            await asyncio.sleep(interval)
        except Exception as e:
            print(f"❌ خطا در ماهیگیری: {e}")
            await asyncio.sleep(15)

# ---------------------------------------------------------
# ۴. پردازش پیام‌ها، منشن‌ها و دکمه‌های بازی Meowie
# ---------------------------------------------------------
@app.on_message(~filters.me & (filters.private | filters.mentioned))
async def handle_mentions_and_afk(client: Client, message: Message):
    if not config["self_active"]:
        return

    # ثبت لاگ تگ‌ها
    if message.mentioned:
        log_entry = f"👤 {message.from_user.first_name if message.from_user else 'ناشناس'} | 💬 چت: {message.chat.title or 'پیوی'} | 📝 متن: {message.text or ''}"
        config["tag_logs"].append(log_entry)
        if len(config["tag_logs"]) > 50:
            config["tag_logs"].pop(0)
        save_config()

    # پاسخ AFK
    if config["afk"]:
        reason = config["afk_reason"] or "در حال حاضر آنلاین نیستم."
        await message.reply(f"🌙 **حالت AFK فعال است**\n💬 علت: {reason}")

@app.on_deleted_messages()
async def handle_deleted(client: Client, messages):
    if config["self_active"] and config["antidel"]:
        for msg in messages:
            if msg.text:
                print(f"🗑 پیام پاک‌شده: {msg.text}")

@app.on_edited_message(~filters.me)
async def handle_edited(client: Client, message: Message):
    if config["self_active"] and config["antiedit"]:
        print(f"✏️ پیام ویرایش‌شده: {message.text}")

# دکمه‌های نجات گربه و صید ماهی
@app.on_message(filters.group & ~filters.me)
async def handle_meowie_game(client: Client, message: Message):
    if not config["self_active"]:
        return

    text = message.text or message.caption or ""

    if config["auto_rescue"] and "نجات پیشی خیابونی" in text:
        if message.reply_markup and message.reply_markup.inline_keyboard:
            for row in message.reply_markup.inline_keyboard:
                for btn in row:
                    if "نجات" in btn.text or "کمک" in btn.text:
                        try:
                            await message.click(btn.text)
                        except Exception as e:
                            print(f"❌ خطا در نجات گربه: {e}")

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
                            except Exception as e:
                                print(f"❌ خطا در کلیک ماهی: {e}")

# ---------------------------------------------------------
# ۵. مدیریت کامل دستورات (فقط از Saved Messages)
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
    s_fish_cmd = "🟢" if config["auto_fish_cmd"] else "🔴"
    
    s_dice = f"🟢 ({config['dice_val']})" if config["dice"] else "🔴"
    s_slot = f"🟢 ({config['slot_val']})" if config["slot"] else "🔴"
    s_basket = "🟢" if config["basket"] else "🔴"
    s_bowl = "🟢" if config["bowl"] else "🔴"

    fish_modes = {"sell": "🟡 فروش", "feed": "🍖 خوراک", "fridge": "❄️ یخچال", "off": "🔴 خاموش"}
    s_fish = fish_modes.get(config["auto_fish_action"], "🔴")

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
🏷 تگ‌های ثبت‌شده: {len(config['tag_logs'])} عدد
🐱 نجات گربه خودکار: {s_rescue}
🎣 ارسال خودکار fish: {s_fish_cmd}
🐟 اقدام ماهیگیری: {s_fish}
───────────────────────
🎲 تاس: {s_dice}
🎰 اسلات: {s_slot}
🏀 بسکتبال: {s_basket}
🎳 بولینگ: {s_bowl}
⏱ سرعت پرتاب: {config['delay']} ثانیه
━━━━━━━ Commands ━━━━━━━

🏷 **تگ‌ها و گزارش‌ها:**
▫️ `.tags` ➔ مشاهده لاگ تگ‌ها
▫️ `.cleartags` ➔ پاکسازی تاریخچه تگ
▫️ `.tag [متن]` ➔ تگ تکی اعضا
▫️ `.all [متن]` ➔ تگ ۵ تایی اعضا
▫️ `.stoptag` ➔ توقف تگ‌زنی

🎲 **تنظیم بازی‌ها:**
▫️ `.rdice on [1-6/even/odd] / .rdice off`
▫️ `.rslot on [1-64/777/bar] / .rslot off`
▫️ `.rbasket on / .rbasket off`
▫️ `.rbowl on / .rbowl off`
▫️ `.rdelay [ثانیه]` ➔ تنظیم سرعت پرتاب

🐱 **بازی Meowie:**
▫️ `.autorescue on/off` ➔ نجات گربه
▫️ `.autofishcmd on <چت_آیدی> <فاصله> [مدت]`
  └ مثال: `.autofishcmd on -100123456789 30m 4h`
▫️ `.autofishcmd off` ➔ خاموش کردن ارسال fish
▫️ `.autofish [sell/feed/fridge/off]`

⚡️ **تنظیمات حساب:**
▫️ `.self on/off` ➔ خاموش/روشن سلف‌بات
▫️ `.clockname` ➔ سوئیچ ساعت اسم
▫️ `.clockbio` ➔ سوئیچ ساعت بیوگرافی
▫️ `.clockstyle [1-4]` ➔ تغییر استایل ساعت
▫️ `.afk [دلیل] / .unafk` ➔ حالت غیبت
▫️ `.antidel on/off` ➔ ضد پاکسازی
▫️ `.antiedit on/off` ➔ ضد ویرایش

💣 **اسپم و ابزارها:**
▫️ `.spam [تعداد] [متن]` ➔ اسپم سریع
▫️ `.delayspam [تاخیر] [تعداد] [متن]` ➔ اسپم با تاخیر
▫️ `.loop [here/آیدی] [ثانیه] [متن]` ➔ ارسال تکراری
▫️ `.stoploop` ➔ توقف ارسال تکراری
▫️ `.del [تعداد] / .purge` ➔ پاکسازی پیام‌ها
▫️ `.calc [عبارت]` ➔ ماشین حساب
▫️ `.type [متن]` ➔ تایپ افکتی
▫️ `.info` ➔ دریافت اطلاعات کاربر
▫️ `.ping` ➔ بررسی سرعت سلف‌بات
"""
    await message.edit(panel_text)

# --- بخش تگ‌ها و گزارش‌ها ---
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
        await message.edit("❌ مثال: `.tag -100123456789 متن` ")
        return
    chat_id = int(args[1])
    tag_text = args[2]
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
        await message.edit("❌ مثال: `.all -100123456789 متن` ")
        return
    chat_id = int(args[1])
    tag_text = args[2]
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

# --- بخش اسپم و ارسال تکراری ---
@app.on_message(filters.me & filters.command("spam", prefixes="."))
async def fast_spam(client: Client, message: Message):
    if not is_saved_messages(client, message): return
    args = message.text.split(maxsplit=3)
    if len(args) < 4:
        await message.edit("❌ مثال: `.spam -100123456789 5 متن` ")
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
        await message.edit("❌ مثال: `.delayspam -100123456789 2 5 متن` ")
        return
    chat_id, delay, count, text = int(args[1]), float(args[2]), int(args[3]), args[4]
    await message.edit("⏱ اسپم با تاخیر شروع شد...")
    for _ in range(count):
        await client.send_message(chat_id, text)
        await asyncio.sleep(delay)

@app.on_message(filters.me & filters.command("loop", prefixes="."))
async def start_loop(client: Client, message: Message):
    if not is_saved_messages(client, message): return
    args = message.text.split(maxsplit=3)
    if len(args) < 4:
        await message.edit("❌ مثال: `.loop -100123456789 10 متن` ")
        return
    config["loop_chat"] = int(args[1])
    config["loop_interval"] = int(args[2])
    config["loop_text"] = args[3]
    config["loop_active"] = True
    save_config()
    await message.edit(f"🔄 ارسال تکراری هر `{args[2]}` ثانیه فعال شد.")

@app.on_message(filters.me & filters.command("stoploop", prefixes="."))
async def stop_loop(client: Client, message: Message):
    if not is_saved_messages(client, message): return
    config["loop_active"] = False
    save_config()
    await message.edit("🛑 ارسال تکراری متوقف شد.")

# --- بخش تنظیمات حساب، ساعت و امنیت ---
@app.on_message(filters.me & filters.command("clockname", prefixes="."))
async def toggle_clock_name(client: Client, message: Message):
    if not is_saved_messages(client, message): return
    config["clock_name"] = not config["clock_name"]
    save_config()
    await message.edit(f"⏰ ساعت اسم: **{'فعال' if config['clock_name'] else 'غیرفعال'}**")

@app.on_message(filters.me & filters.command("clockbio", prefixes="."))
async def toggle_clock_bio(client: Client, message: Message):
    if not is_saved_messages(client, message): return
    config["clock_bio"] = not config["clock_bio"]
    save_config()
    await message.edit(f"📝 ساعت بیو: **{'فعال' if config['clock_bio'] else 'غیرفعال'}**")

@app.on_message(filters.me & filters.command("clockstyle", prefixes="."))
async def change_clock_style(client: Client, message: Message):
    if not is_saved_messages(client, message): return
    args = message.text.split()
    if len(args) > 1 and args[1].isdigit():
        config["clock_style"] = int(args[1])
        save_config()
        await message.edit(f"🎨 استایل ساعت روی **{args[1]}** تنظیم شد.")

@app.on_message(filters.me & filters.command("afk", prefixes="."))
async def set_afk(client: Client, message: Message):
    if not is_saved_messages(client, message): return
    args = message.text.split(maxsplit=1)
    config["afk"] = True
    config["afk_reason"] = args[1] if len(args) > 1 else ""
    save_config()
    await message.edit("🌙 حالت AFK فعال شد.")

@app.on_message(filters.me & filters.command("unafk", prefixes="."))
async def set_unafk(client: Client, message: Message):
    if not is_saved_messages(client, message): return
    config["afk"] = False
    save_config()
    await message.edit("☀️ حالت AFK غیرفعال شد.")

@app.on_message(filters.me & filters.command("antidel", prefixes="."))
async def toggle_antidel(client: Client, message: Message):
    if not is_saved_messages(client, message): return
    args = message.text.split()
    if len(args) > 1:
        config["antidel"] = (args[1].lower() == "on")
        save_config()
        await message.edit(f"🛡 ضد پاکسازی: **{args[1].upper()}**")

@app.on_message(filters.me & filters.command("antiedit", prefixes="."))
async def toggle_antiedit(client: Client, message: Message):
    if not is_saved_messages(client, message): return
    args = message.text.split()
    if len(args) > 1:
        config["antiedit"] = (args[1].lower() == "on")
        save_config()
        await message.edit(f"✏️ ضد ویرایش: **{args[1].upper()}**")

# --- بخش ابزارها، پاکسازی و محاسبات ---
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

# --- بخش تنظیمات ماهیگیری و نجات گربه ---
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

                if len(args) >= 5:
                    stop_str = args[4].lower()
                    stop_sec = int(stop_str.replace("h", "")) * 3600 if stop_str.endswith("h") else int(stop_str.replace("m", "")) * 60
                    config["auto_fish_stop_time"] = time.time() + stop_sec
                else:
                    config["auto_fish_stop_time"] = 0

                save_config()
                await message.edit(f"✅ ارسال خودکار `fish` فعال شد.")
                await client.send_message(target_chat, "fish")
            except Exception as e:
                await message.edit("❌ فرمت دستور اشتباه است.")
        elif opt == "off":
            config["auto_fish_cmd"] = False
            config["auto_fish_stop_time"] = 0
            save_config()
            await message.edit("❌ ارسال خودکار `fish` غیرفعال شد.")

@app.on_message(filters.me & filters.command("autofish", prefixes="."))
async def set_auto_fish(client: Client, message: Message):
    if not is_saved_messages(client, message): return
    args = message.text.split()
    if len(args) > 1 and args[1].lower() in ["sell", "feed", "fridge", "off"]:
        config["auto_fish_action"] = args[1].lower()
        save_config()
        await message.edit(f"✅ اقدام ماهیگیری روی **{args[1]}** تنظیم شد.")

@app.on_message(filters.me & filters.command("autorescue", prefixes="."))
async def set_auto_rescue(client: Client, message: Message):
    if not is_saved_messages(client, message): return
    args = message.text.split()
    if len(args) > 1:
        config["auto_rescue"] = (args[1].lower() == "on")
        save_config()
        await message.edit(f"✅ نجات خودکار گربه: **{args[1].upper()}**")

# ---------------------------------------------------------
# ۶. اجرای پس‌زمینه و اصلی
# ---------------------------------------------------------
if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.create_task(background_clock())
    loop.create_task(auto_loop_task())
    loop.create_task(auto_fish_loop())
    print("Momo Selfbot Fully Running...")
    app.run()
