import os
import re
import asyncio
from datetime import datetime
from pyrogram import Client, filters
from pyrogram.errors import FloodWait

# ==========================================================
# 1. تنظیمات و پیکربندی سیشن (Session Setup)
# ==========================================================
API_ID = int(os.environ.get("API_ID", 0))
API_HASH = os.environ.get("API_HASH", "")
SESSION_STRING = os.environ.get("SESSION_STRING", "")

app = Client(
    "stealth_selfbot",
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=SESSION_STRING,
    in_memory=True
)

# ==========================================================
# 2. حافظه و وضعیت متغیرهای سیستم (Bot State)
# ==========================================================
bot_data = {
    "clock": False,
    "clock_style": 1,
    "clock_task": None,
    "original_name": "",
    "afk": False,
    "afk_reason": "",
    "antidel": True,
    "pmbot": False,
    "pmbot_text": "سلام! من در حال حاضر آنلاین نیستم، به‌زودی پاسخ می‌دهم.",
    "tags_log": [],
    "tagging_active": False,
    "loop_tasks": [],
    
    # تنظیمات بازی‌ها
    "games": {
        "dice": {"active": False, "target": "6"},
        "slot": {"active": False},
        "basket": {"active": False, "target": [4, 5]},
        "bowl": {"active": False, "target": [6]},
        "delay": 0.25
    },
    "game_task": None
}

# ==========================================================
# 3. داشبورد و مدیریت سیستم (.panel)
# ==========================================================
def get_status_emoji(condition):
    return "🟢 فعال" if condition else "🔴 خاموش"

@app.on_message(filters.command(["panel", "help"], prefixes=".") & filters.me)
async def show_panel(client, message):
    g = bot_data["games"]
    panel_text = (
        "📋 **داشبورد سلف‌بات اختصاصی A**\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"⏰ **ساعت اسم:** [{get_status_emoji(bot_data['clock'])} | استایل {bot_data['clock_style']}]\n"
        f"🌙 **حالت AFK:** [{get_status_emoji(bot_data['afk'])}]\n"
        f"🛡 **ضد پاکسازی:** [{get_status_emoji(bot_data['antidel'])}]\n"
        f"🤖 **منشی پیوی:** [{get_status_emoji(bot_data['pmbot'])}]\n"
        f"🏷 **تگ‌های ثبت‌شده:** [{len(bot_data['tags_log'])} عدد]\n\n"
        f"🎲 **تاس شانس:** [{get_status_emoji(g['dice']['active'])}]\n"
        f"🎰 **اسلات شانس:** [{get_status_emoji(g['slot']['active'])}]\n"
        f"🏀 **بسکتبال:** [{get_status_emoji(g['basket']['active'])}]\n"
        f"🎳 **بولینگ:** [{get_status_emoji(g['bowl']['active'])}]\n"
        f"⏱ **سرعت پرتاب:** [{g['delay']} ثانیه]\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "🛠 **راهنمای دستورات سیستم:**\n\n"
        "🏷 **تگ‌ها و گزارش‌ها:**\n"
        "• `.tags` ➔ مشاهده پیام‌هایی که تگ شده‌اید\n"
        "• `.cleartags` ➔ پاکسازی تاریخچه تگ‌ها\n"
        "• `.tag [پیام]` ➔ تگ تکی اعضای گروه\n"
        "• `.all [پیام]` ➔ تگ ۵ تایی اعضای گروه\n"
        "• `.tagfast [پیام]` ➔ تگ پرسرعت اعضا\n"
        "• `.stoptag` ➔ توقف عملیات تگ‌زنی\n\n"
        "🎲 **بازی‌ها و پرتاب هوشمند:**\n"
        "• `.rdice on [even/odd/1-6]` ➔ تنظیم و شروع تاس\n"
        "• `.rdice off` ➔ غیرفعال‌سازی تاس\n"
        "• `.rslot on / off` ➔ فعال/غیرفعال اسلات\n"
        "• `.rbasket on / off` ➔ بسکتبال\n"
        "• `.rbowl on / off` ➔ بولینگ\n"
        "• `.rdelay [ثانیه]` ➔ تنظیم سرعت پرتاب\n\n"
        "⚡️ **تنظیمات حساب:**\n"
        "• `.clock` ➔ روشن/خاموش ساعت روی اسم\n"
        "• `.clockstyle [1-4]` ➔ تغییر استایل فونت ساعت\n"
        "• `.afk [دلیل]` / `.unafk` ➔ حالت غیبت\n"
        "• `.pmbot on / off` ➔ منشی خودکار پیوی\n"
        "• `.antidel on / off` ➔ ضد پاکسازی پیام\n\n"
        "💣 **اسپم و ابزارهای خودکار:**\n"
        "• `.spam [تعداد] [متن]` ➔ اسپم سریع\n"
        "• `.delayspam [تاخیر] [تعداد] [متن]` ➔ اسپم با زمان‌بندی\n"
        "• `.loop [here/آیدی] [ثانیه] [متن]` ➔ ارسال تکراری\n"
        "• `.stoploop` ➔ توقف تمام حلقه‌ها\n"
        "• `.del [تعداد]` ➔ پاکسازی پیام‌های شما\n"
        "• `.purge` ➔ پاکسازی گروهی (با ریپلای)\n"
        "• `.calc [عبارت]` ➔ ماشین حساب\n"
        "• `.type [متن]` ➔ تایپ افکتی\n"
        "• `.font [متن]` ➔ ساخت فونت زیبایی\n"
        "• `.info` ➔ دریافت اطلاعات کاربر\n"
        "• `.ping` ➔ بررسی سرعت سلف‌بات"
    )
    await message.edit_text(panel_text)

# ==========================================================
# 4. سیستم موتور پرتاب خودکار (Dice & Games Automation)
# ==========================================================
async def game_runner(client, chat_id, emoji, check_win_func):
    while True:
        try:
            sent = await client.send_dice(chat_id, emoji=emoji)
            val = sent.dice.value
            
            if check_win_func(val):
                await client.send_message(chat_id, f"🎯 **به هدف رسیدیم! نتیجه:** {val}")
                break
            else:
                await asyncio.sleep(0.5)
                await sent.delete()
                
            await asyncio.sleep(bot_data["games"]["delay"])
        except FloodWait as e:
            await asyncio.sleep(e.value + 1)
        except Exception:
            break

@app.on_message(filters.command("rdice", prefixes=".") & filters.me)
async def handle_rdice(client, message):
    args = message.text.split()
    await message.delete()
    if len(args) > 1 and args[1] == "on":
        target = args[2] if len(args) > 2 else "6"
        bot_data["games"]["dice"]["active"] = True
        
        def win_check(v):
            if target == "even": return v % 2 == 0
            if target == "odd": return v % 2 != 0
            return str(v) == target
            
        bot_data["game_task"] = asyncio.create_task(game_runner(client, message.chat.id, "🎲", win_check))
    else:
        bot_data["games"]["dice"]["active"] = False
        if bot_data["game_task"]: bot_data["game_task"].cancel()

@app.on_message(filters.command("rslot", prefixes=".") & filters.me)
async def handle_rslot(client, message):
    args = message.text.split()
    await message.delete()
    if len(args) > 1 and args[1] == "on":
        bot_data["games"]["slot"]["active"] = True
        bot_data["game_task"] = asyncio.create_task(game_runner(client, message.chat.id, "🎰", lambda v: v == 64))
    else:
        bot_data["games"]["slot"]["active"] = False
        if bot_data["game_task"]: bot_data["game_task"].cancel()

@app.on_message(filters.command("rbasket", prefixes=".") & filters.me)
async def handle_rbasket(client, message):
    args = message.text.split()
    await message.delete()
    if len(args) > 1 and args[1] == "on":
        bot_data["games"]["basket"]["active"] = True
        bot_data["game_task"] = asyncio.create_task(game_runner(client, message.chat.id, "🏀", lambda v: v in [4, 5]))
    else:
        bot_data["games"]["basket"]["active"] = False
        if bot_data["game_task"]: bot_data["game_task"].cancel()

@app.on_message(filters.command("rbowl", prefixes=".") & filters.me)
async def handle_rbowl(client, message):
    args = message.text.split()
    await message.delete()
    if len(args) > 1 and args[1] == "on":
        bot_data["games"]["bowl"]["active"] = True
        bot_data["game_task"] = asyncio.create_task(game_runner(client, message.chat.id, "🎳", lambda v: v == 6))
    else:
        bot_data["games"]["bowl"]["active"] = False
        if bot_data["game_task"]: bot_data["game_task"].cancel()

@app.on_message(filters.command("rdelay", prefixes=".") & filters.me)
async def set_rdelay(client, message):
    args = message.text.split()
    if len(args) > 1:
        try:
            val = float(args[1])
            bot_data["games"]["delay"] = val
            await message.edit_text(f"⏱ **سرعت پرتاب روی {val} ثانیه تنظیم شد.**")
        except ValueError:
            await message.edit_text("❌ **عدد وارد شده معتبر نیست.**")

# ==========================================================
# 5. دستورات اسپم و ارسال تکراری (Spam & Loop)
# ==========================================================
@app.on_message(filters.command("spam", prefixes=".") & filters.me)
async def do_spam(client, message):
    args = message.text.split(maxsplit=2)
    await message.delete()
    if len(args) >= 3 and args[1].isdigit():
        count = int(args[1])
        text = args[2]
        for _ in range(count):
            await client.send_message(message.chat.id, text)
            await asyncio.sleep(0.1)

@app.on_message(filters.command("delayspam", prefixes=".") & filters.me)
async def do_delayspam(client, message):
    args = message.text.split(maxsplit=3)
    await message.delete()
    if len(args) >= 4:
        try:
            delay = float(args[1])
            count = int(args[2])
            text = args[3]
            for _ in range(count):
                await client.send_message(message.chat.id, text)
                await asyncio.sleep(delay)
        except Exception:
            pass

async def loop_worker(client, target_chat, delay, text):
    while True:
        try:
            await client.send_message(target_chat, text)
            await asyncio.sleep(delay)
        except asyncio.CancelledError:
            break
        except Exception:
            await asyncio.sleep(delay)

@app.on_message(filters.command("loop", prefixes=".") & filters.me)
async def start_loop(client, message):
    args = message.text.split(maxsplit=3)
    await message.delete()
    if len(args) >= 4:
        target = message.chat.id if args[1] == "here" else args[1]
        try:
            delay = float(args[2])
            text = args[3]
            task = asyncio.create_task(loop_worker(client, target, delay, text))
            bot_data["loop_tasks"].append(task)
        except Exception:
            pass

@app.on_message(filters.command("stoploop", prefixes=".") & filters.me)
async def stop_loops(client, message):
    for task in bot_data["loop_tasks"]:
        task.cancel()
    bot_data["loop_tasks"].clear()
    await message.edit_text("🛑 **تمامی حلقه‌های ارسال متوقف شدند.**")

# ==========================================================
# 6. تگ‌زن و لاگر تگ‌ها (Tagging System)
# ==========================================================
@app.on_message(filters.command(["tag", "all", "tagfast"], prefixes=".") & filters.me)
async def tag_handler(client, message):
    cmd = message.command[0]
    args = message.text.split(maxsplit=1)
    text = args[1] if len(args) > 1 else "پینگ"
    await message.delete()
    
    bot_data["tagging_active"] = True
    chat_id = message.chat.id
    step = 5 if cmd == "all" else 1
    delay = 0.5 if cmd == "tagfast" else 1.5
    
    members = []
    async for m in client.get_chat_members(chat_id):
        if not m.user.is_bot and not m.user.is_deleted:
            members.append(m.user)
            
    for i in range(0, len(members), step):
        if not bot_data["tagging_active"]:
            break
        chunk = members[i:i+step]
        mentions = " ".join([f"[{u.first_name}](tg://user?id={u.id})" for u in chunk])
        await client.send_message(chat_id, f"{text}\n{mentions}")
        await asyncio.sleep(delay)

@app.on_message(filters.command("stoptag", prefixes=".") & filters.me)
async def stop_tag(client, message):
    bot_data["tagging_active"] = False
    await message.edit_text("🛑 **عملیات تگ‌زنی متوقف شد.**")

@app.on_message(filters.mentioned & ~filters.me)
async def log_mentions(client, message):
    log_text = f"📌 تگ در **{message.chat.title or 'چت'}** توسط [{message.from_user.first_name}](tg://user?id={message.from_user.id})"
    bot_data["tags_log"].append(log_text)
    if len(bot_data["tags_log"]) > 50:
        bot_data["tags_log"].pop(0)

@app.on_message(filters.command("tags", prefixes=".") & filters.me)
async def show_tags(client, message):
    if not bot_data["tags_log"]:
        await message.edit_text("📜 **هیچ تگی ثبت نشده است.**")
    else:
        logs = "\n".join(bot_data["tags_log"][-10:])
        await message.edit_text(f"📜 **آخرین تگ‌های شما:**\n\n{logs}")

@app.on_message(filters.command("cleartags", prefixes=".") & filters.me)
async def clear_tags(client, message):
    bot_data["tags_log"].clear()
    await message.edit_text("🧹 **تاریخچه تگ‌ها پاکسازی شد.**")

# ==========================================================
# 7. تنظیمات حساب (Clock, AFK, PMBot, AntiDel)
# ==========================================================
FONT_STYLES = {
    1: {"0": "۰", "1": "۱", "2": "۲", "3": "۳", "4": "۴", "5": "۵", "6": "۶", "7": "۷", "8": "۸", "9": "۹"},
    2: {"0": "𝟎", "1": "𝟏", "2": "𝟐", "3": "𝟑", "4": "𝟒", "5": "𝟓", "6": "𝟔", "7": "𝟕", "8": "𝟖", "9": "𝟗"},
    3: {"0": "⓪", "1": "①", "2": "②", "3": "③", "4": "④", "5": "⑤", "6": "⑥", "7": "⑦", "8": "⑧", "9": "⑨"},
    4: {"0": "0", "1": "1", "2": "2", "3": "3", "4": "4", "5": "5", "6": "6", "7": "7", "8": "8", "9": "9"}
}

async def clock_loop(client):
    while True:
        try:
            me = await client.get_me()
            if not bot_data["original_name"]:
                bot_data["original_name"] = me.first_name
            
            raw_time = datetime.now().strftime("%H:%M")
            style_dict = FONT_STYLES.get(bot_data["clock_style"], FONT_STYLES[1])
            styled_time = "".join(style_dict.get(c, c) for c in raw_time)
            
            await client.update_profile(first_name=f"{bot_data['original_name']} [{styled_time}]")
            await asyncio.sleep(60)
        except asyncio.CancelledError:
            if bot_data["original_name"]:
                await client.update_profile(first_name=bot_data["original_name"])
            break
        except Exception:
            await asyncio.sleep(60)

@app.on_message(filters.command("clock", prefixes=".") & filters.me)
async def toggle_clock(client, message):
    bot_data["clock"] = not bot_data["clock"]
    if bot_data["clock"]:
        bot_data["clock_task"] = asyncio.create_task(clock_loop(client))
        await message.edit_text("⏰ **ساعت روی اسم فعال شد.**")
    else:
        if bot_data["clock_task"]: bot_data["clock_task"].cancel()
        await message.edit_text("⏰ **ساعت روی اسم خاموش شد.**")

@app.on_message(filters.command("clockstyle", prefixes=".") & filters.me)
async def set_clockstyle(client, message):
    args = message.text.split()
    if len(args) > 1 and args[1].isdigit() and int(args[1]) in [1, 2, 3, 4]:
        bot_data["clock_style"] = int(args[1])
        await message.edit_text(f"🎨 **استایل ساعت به حالت {args[1]} تغییر کرد.**")

@app.on_message(filters.command("afk", prefixes=".") & filters.me)
async def set_afk(client, message):
    reason = message.text.split(maxsplit=1)[1] if len(message.text.split()) > 1 else "ثبت نشده"
    bot_data["afk"] = True
    bot_data["afk_reason"] = reason
    await message.edit_text(f"🌙 **حالت AFK فعال شد.**\n📝 علت: {reason}")

@app.on_message(filters.command("unafk", prefixes=".") & filters.me)
async def unset_afk(client, message):
    bot_data["afk"] = False
    await message.edit_text("☀️ **حالت AFK غیرفعال شد.**")

@app.on_message(filters.command("pmbot", prefixes=".") & filters.me)
async def toggle_pmbot(client, message):
    args = message.text.split()
    if len(args) > 1:
        bot_data["pmbot"] = (args[1] == "on")
        status = "فعال" if bot_data["pmbot"] else "خاموش"
        await message.edit_text(f"🤖 **منشی پیوی {status} شد.**")

@app.on_message(filters.command("antidel", prefixes=".") & filters.me)
async def toggle_antidel(client, message):
    args = message.text.split()
    if len(args) > 1:
        bot_data["antidel"] = (args[1] == "on")
        status = "فعال" if bot_data["antidel"] else "خاموش"
        await message.edit_text(f"🛡 **ضد پاکسازی {status} شد.**")

@app.on_message(filters.private & ~filters.me & ~filters.bot, group=1)
async def pm_handler(client, message):
    if bot_data["afk"]:
        await message.reply_text(f"👋 **در حال حاضر آنلاین نیستم.**\n📝 **علت:** {bot_data['afk_reason']}")
    elif bot_data["pmbot"]:
        await message.reply_text(bot_data["pmbot_text"])

# ==========================================================
# 8. ابزارهای کاربردی (Tools & Utilities)
# ==========================================================
@app.on_message(filters.command("del", prefixes=".") & filters.me)
async def delete_my_msgs(client, message):
    args = message.text.split()
    if len(args) > 1 and args[1].isdigit():
        count = int(args[1])
        await message.delete()
        async for m in client.get_chat_history(message.chat.id, limit=count * 2):
            if m.from_user and m.from_user.is_self:
                await m.delete()

@app.on_message(filters.command("purge", prefixes=".") & filters.me)
async def purge_msgs(client, message):
    if message.reply_to_message:
        start_id = message.reply_to_message.id
        end_id = message.id
        msg_ids = list(range(start_id, end_id + 1))
        await client.delete_messages(message.chat.id, msg_ids)

@app.on_message(filters.command("calc", prefixes=".") & filters.me)
async def calculate(client, message):
    expr = message.text.split(maxsplit=1)
    if len(expr) > 1:
        try:
            res = eval(re.sub(r'[^0-9\+\-\*\/\(\)\.]', '', expr[1]))
            await message.edit_text(f"🔢 **نتیجه:** `{res}`")
        except Exception:
            await message.edit_text("❌ **عبارت ریاضی نامعتبر است.**")

@app.on_message(filters.command("type", prefixes=".") & filters.me)
async def typewriter(client, message):
    text = message.text.split(maxsplit=1)[1] if len(message.text.split()) > 1 else ""
    typed = ""
    for char in text:
        typed += char
        await message.edit_text(f"{typed}▒")
        await asyncio.sleep(0.1)
    await message.edit_text(typed)

@app.on_message(filters.command("font", prefixes=".") & filters.me)
async def font_style(client, message):
    text = message.text.split(maxsplit=1)[1] if len(message.text.split()) > 1 else ""
    f_text = text.translate(str.maketrans("abcdefghijklmnopqrstuvwxyz", "𝕒𝕓𝕔𝕕𝕖𝕗𝕘𝕙𝕚𝕛𝕜𝕝𝕞𝕟𝕠𝕡𝕢𝕣𝕤𝕥𝕦𝕧𝕨𝕩𝕪𝕫"))
    await message.edit_text(f_text)

@app.on_message(filters.command("info", prefixes=".") & filters.me)
async def user_info(client, message):
    user = message.reply_to_message.from_user if message.reply_to_message else message.from_user
    info = (
        f"👤 **اطلاعات کاربر:**\n"
        f"├ **نام:** {user.first_name}\n"
        f"├ **آیدی عددی:** `{user.id}`\n"
        f"└ **یوزرنیم:** @{user.username if user.username else 'ندارد'}"
    )
    await message.edit_text(info)

@app.on_message(filters.command("ping", prefixes=".") & filters.me)
async def ping_pong(client, message):
    start = datetime.now()
    await message.edit_text("🏓 **Pong!**")
    end = datetime.now()
    ms = (end - start).microseconds / 1000
    await message.edit_text(f"🏓 **Pong!**\n⚡️ **سرعت پاسخگویی:** `{ms}ms`")

# ==========================================================
# 9. اجرای برنامه (Run Client)
# ==========================================================
if __name__ == "__main__":
    print("Self-bot is running with full dashboard features...")
    app.run()
