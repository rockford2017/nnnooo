import os
import re
import asyncio
from datetime import datetime
from pyrogram import Client, filters
from pyrogram.errors import FloodWait

# ==========================================================
# 1. تنظیمات سیشن (Session Setup)
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
# 2. وضعیت سیستم (Bot State)
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
    "pmbot_text": "سلام! در حال حاضر آنلاین نیستم، به‌زودی پاسخ می‌دهم.",
    "tags_log": [],
    "tagging_active": False,
    "loop_tasks": [],
    
    # تنظیمات بازی‌ها
    "games": {
        "dice": False,
        "dice_target": "6",
        "slot": False,
        "slot_target": "64",  # پیش‌فرض: سه تا ۷ (64)
        "basket": False,
        "bowl": False,
        "delay": 0.25
    },
    "is_rolling": False  # جلوگیری از تداخل پرتاب‌ها
}

async def safe_delete(message):
    try:
        me = await message._client.get_me()
        if message.chat.id != me.id:
            await message.delete()
    except Exception:
        pass

# ==========================================================
# 3. داشبورد و وضعیت (.panel / .help)
# ==========================================================
def get_status(condition):
    return "🟢" if condition else "🔴"

@app.on_message(filters.command(["panel", "help"], prefixes=".") & filters.me)
async def show_panel(client, message):
    g = bot_data["games"]
    panel_text = (
        "📋 **داشبورد سلف‌بات اختصاصی A**\n"
        "━━━━━━━ Status ━━━━━━━\n"
        f"⏰ **ساعت اسم:** {get_status(bot_data['clock'])} (استایل {bot_data['clock_style']})\n"
        f"🌙 **حالت AFK:** {get_status(bot_data['afk'])}\n"
        f"🛡 **ضد پاکسازی:** {get_status(bot_data['antidel'])}\n"
        f"🤖 **منشی پیوی:** {get_status(bot_data['pmbot'])}\n"
        f"🏷 **تگ‌های ثبت‌شده:** `{len(bot_data['tags_log'])}` عدد\n"
        "───────────────────────\n"
        f"🎲 **تاس:** {get_status(g['dice'])} (هدف: {g['dice_target']})\n"
        f"🎰 **اسلات:** {get_status(g['slot'])} (هدف: {g['slot_target']})\n"
        f"🏀 **بسکتبال:** {get_status(g['basket'])}\n"
        f"🎳 **بولینگ:** {get_status(g['bowl'])}\n"
        f"⏱ **سرعت پرتاب:** `{g['delay']}` ثانیه\n"
        "━━━━━━━ Commands ━━━━━━━\n\n"
        "🏷 **تگ‌ها و گزارش‌ها:**\n"
        "▫️ `.tags` ➔ مشاهده لاگ تگ‌ها\n"
        "▫️ `.cleartags` ➔ پاکسازی تاریخچه تگ\n"
        "▫️ `.tag [متن]` ➔ تگ تکی اعضا\n"
        "▫️ `.all [متن]` ➔ تگ ۵ تایی اعضا\n"
        "▫️ `.tagfast [متن]` ➔ تگ سریع اعضا\n"
        "▫️ `.stoptag` ➔ توقف تگ‌زنی\n\n"
        "🎲 **تنظیم بازی‌ها:**\n"
        "▫️ `.rdice on [even/odd/1-6]` / `.rdice off` ➔ تنظیم تاس\n"
        "▫️ `.rslot on [777/bar/grape/lemon/1-64]` / `.rslot off` ➔ تنظیم اسلات\n"
        "▫️ `.rbasket on` / `.rbasket off` ➔ تنظیم بسکتبال\n"
        "▫️ `.rbowl on` / `.rbowl off` ➔ تنظیم بولینگ\n"
        "▫️ `.rdelay [ثانیه]` ➔ تنظیم سرعت پرتاب\n\n"
        "⚡️ **تنظیمات حساب:**\n"
        "▫️ `.clock` ➔ سوئیچ ساعت اسم\n"
        "▫️ `.clockstyle [1-4]` ➔ تغییر استایل ساعت\n"
        "▫️ `.afk [دلیل]` / `.unafk` ➔ حالت غیبت\n"
        "▫️ `.pmbot on / off` ➔ منشی خودکار\n"
        "▫️ `.antidel on / off` ➔ ضد پاکسازی\n\n"
        "💣 **اسپم و ابزارها:**\n"
        "▫️ `.spam [تعداد] [متن]` ➔ اسپم سریع\n"
        "▫️ `.delayspam [تاخیر] [تعداد] [متن]` ➔ اسپم با تاخیر\n"
        "▫️ `.loop [here/آیدی] [ثانیه] [متن]` ➔ ارسال تکراری\n"
        "▫️ `.stoploop` ➔ توقف تمام حلقه‌ها\n"
        "▫️ `.del [تعداد]` ➔ پاکسازی پیام‌های شما\n"
        "▫️ `.purge` ➔ پاکسازی گروهی (با ریپلای)\n"
        "▫️ `.calc [عبارت]` ➔ ماشین حساب\n"
        "▫️ `.type [متن]` ➔ تایپ افکتی\n"
        "▫️ `.font [متن]` ➔ فونت زیبایی انگلیسی\n"
        "▫️ `.info` ➔ دریافت اطلاعات کاربر\n"
        "▫️ `.ping` ➔ بررسی سرعت سلف‌بات"
    )
    await message.edit_text(panel_text)

# ==========================================================
# 4. دستورات فعال‌سازی اولیه بازی‌ها
# ==========================================================
@app.on_message(filters.command("rdice", prefixes=".") & filters.me)
async def set_rdice(client, message):
    args = message.text.split()
    if len(args) > 1 and args[1] == "on":
        target = args[2] if len(args) > 2 else "6"
        if target not in ["even", "odd"] and not (target.isdigit() and 1 <= int(target) <= 6):
            target = "6"
        bot_data["games"]["dice"] = True
        bot_data["games"]["dice_target"] = target
        await message.edit_text(f"🎲 **تاس فعال شد (هدف: {target}).**")
    else:
        bot_data["games"]["dice"] = False
        await message.edit_text("🎲 **تاس خاموش شد.**")

@app.on_message(filters.command("rslot", prefixes=".") & filters.me)
async def set_rslot(client, message):
    args = message.text.split()
    if len(args) > 1 and args[1] == "on":
        target_input = args[2].lower() if len(args) > 2 else "777"
        
        # نگاشت کلمات به کد عددی اسلات
        mapping = {
            "777": "64",
            "bar": "1",
            "grape": "22",
            "grapes": "22",
            "lemon": "43"
        }
        
        target = mapping.get(target_input, target_input)
        if not (target.isdigit() and 1 <= int(target) <= 64):
            target = "64"
            
        bot_data["games"]["slot"] = True
        bot_data["games"]["slot_target"] = target
        await message.edit_text(f"🎰 **اسلات فعال شد (هدف: {target_input} / کد {target}).**")
    else:
        bot_data["games"]["slot"] = False
        await message.edit_text("🎰 **اسلات خاموش شد.**")

@app.on_message(filters.command("rbasket", prefixes=".") & filters.me)
async def set_rbasket(client, message):
    args = message.text.split()
    if len(args) > 1 and args[1] == "on":
        bot_data["games"]["basket"] = True
        await message.edit_text("🏀 **بسکتبال فعال شد.**")
    else:
        bot_data["games"]["basket"] = False
        await message.edit_text("🏀 **بسکتبال خاموش شد.**")

@app.on_message(filters.command("rbowl", prefixes=".") & filters.me)
async def set_rbowl(client, message):
    args = message.text.split()
    if len(args) > 1 and args[1] == "on":
        bot_data["games"]["bowl"] = True
        await message.edit_text("🎳 **بولینگ فعال شد.**")
    else:
        bot_data["games"]["bowl"] = False
        await message.edit_text("🎳 **بولینگ خاموش شد.**")

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
# 5. موتور ماشه‌ای پرتاب هوشمند
# ==========================================================
@app.on_message(filters.dice & filters.me)
async def dice_trigger(client, message):
    if bot_data["is_rolling"]:
        return

    emoji = message.dice.emoji
    g = bot_data["games"]
    
    is_active = False
    check_win = None
    
    if emoji == "🎲" and g["dice"]:
        is_active = True
        t = g["dice_target"]
        check_win = lambda v: (v % 2 == 0) if t == "even" else ((v % 2 != 0) if t == "odd" else str(v) == t)
    elif emoji == "🎰" and g["slot"]:
        is_active = True
        t = g["slot_target"]
        check_win = lambda v: str(v) == t
    elif emoji == "🏀" and g["basket"]:
        is_active = True
        check_win = lambda v: v in [4, 5]
    elif emoji == "🎳" and g["bowl"]:
        is_active = True
        check_win = lambda v: v == 6
        
    if not is_active or not check_win:
        return

    bot_data["is_rolling"] = True
    chat_id = message.chat.id
    current_msg = message

    while True:
        # کنترل خاموش شدن دستی در حین چرخش
        if emoji == "🎲" and not g["dice"]:
            break
        if emoji == "🎰" and not g["slot"]:
            break
        if emoji == "🏀" and not g["basket"]:
            break
        if emoji == "🎳" and not g["bowl"]:
            break

        val = current_msg.dice.value
        if check_win(val):
            break
        else:
            await asyncio.sleep(0.1)
            await current_msg.delete()
            await asyncio.sleep(g["delay"])
            try:
                current_msg = await client.send_dice(chat_id, emoji=emoji)
            except FloodWait as e:
                await asyncio.sleep(e.value + 1)
                current_msg = await client.send_dice(chat_id, emoji=emoji)
            except Exception:
                break
                
    bot_data["is_rolling"] = False

# ==========================================================
# 6. سایر ابزارها (Spam, Tags, Account, Tools)
# ==========================================================
@app.on_message(filters.command("spam", prefixes=".") & filters.me)
async def do_spam(client, message):
    args = message.text.split(maxsplit=2)
    await safe_delete(message)
    if len(args) >= 3 and args[1].isdigit():
        for _ in range(int(args[1])):
            await client.send_message(message.chat.id, args[2])
            await asyncio.sleep(0.1)

@app.on_message(filters.command("delayspam", prefixes=".") & filters.me)
async def do_delayspam(client, message):
    args = message.text.split(maxsplit=3)
    await safe_delete(message)
    if len(args) >= 4:
        try:
            for _ in range(int(args[2])):
                await client.send_message(message.chat.id, args[3])
                await asyncio.sleep(float(args[1]))
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
    if len(args) >= 4:
        target_str = args[1]
        target = message.chat.id if target_str == "here" else target_str
        try:
            task = asyncio.create_task(loop_worker(client, target, float(args[2]), args[3]))
            bot_data["loop_tasks"].append(task)
            await message.edit_text(f"🔄 **حلقه ارسال فعال شد در `{target_str}`**")
        except Exception as e:
            await message.edit_text(f"❌ **خطا:** `{str(e)}`")

@app.on_message(filters.command("stoploop", prefixes=".") & filters.me)
async def stop_loops(client, message):
    for task in bot_data["loop_tasks"]: task.cancel()
    bot_data["loop_tasks"].clear()
    await message.edit_text("🛑 **تمامی حلقه‌ها متوقف شدند.**")

@app.on_message(filters.command(["tag", "all", "tagfast"], prefixes=".") & filters.me)
async def tag_handler(client, message):
    cmd = message.command[0]
    args = message.text.split(maxsplit=1)
    text = args[1] if len(args) > 1 else "پینگ"
    await safe_delete(message)
    
    bot_data["tagging_active"] = True
    step = 5 if cmd == "all" else 1
    delay = 0.5 if cmd == "tagfast" else 1.5
    
    members = [m.user async for m in client.get_chat_members(message.chat.id) if not m.user.is_bot and not m.user.is_deleted]
    for i in range(0, len(members), step):
        if not bot_data["tagging_active"]: break
        mentions = " ".join([f"[{u.first_name}](tg://user?id={u.id})" for u in members[i:i+step]])
        await client.send_message(message.chat.id, f"{text}\n{mentions}")
        await asyncio.sleep(delay)

@app.on_message(filters.command("stoptag", prefixes=".") & filters.me)
async def stop_tag(client, message):
    bot_data["tagging_active"] = False
    await message.edit_text("🛑 **تگ‌زنی متوقف شد.**")

@app.on_message(filters.mentioned & ~filters.me)
async def log_mentions(client, message):
    user = message.from_user
    chat = message.chat
    user_link = f"[{user.first_name}](tg://user?id={user.id})" if user else "کاربر"
    msg_link = f"https://t.me/{chat.username}/{message.id}" if chat.username else f"https://t.me/c/{str(chat.id).replace('-100', '')}/{message.id}"
    bot_data["tags_log"].append(f"📌 [{datetime.now().strftime('%H:%M')}] {user_link} در **[{chat.title or 'پیوی'}]({msg_link})**")
    if len(bot_data["tags_log"]) > 50: bot_data["tags_log"].pop(0)

@app.on_message(filters.command("tags", prefixes=".") & filters.me)
async def show_tags(client, message):
    await message.edit_text(f"📜 **آخرین تگ‌ها:**\n\n" + "\n".join(bot_data["tags_log"][-10:]) if bot_data["tags_log"] else "📜 **تگی ثبت نشده.**", disable_web_page_preview=True)

@app.on_message(filters.command("cleartags", prefixes=".") & filters.me)
async def clear_tags(client, message):
    bot_data["tags_log"].clear()
    await message.edit_text("🧹 **تاریخچه پاک شد.**")

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
            if not bot_data["original_name"]: bot_data["original_name"] = me.first_name
            styled = "".join(FONT_STYLES.get(bot_data["clock_style"], FONT_STYLES[1]).get(c, c) for c in datetime.now().strftime("%H:%M"))
            await client.update_profile(first_name=f"{bot_data['original_name']} [{styled}]")
            await asyncio.sleep(60)
        except asyncio.CancelledError:
            if bot_data["original_name"]: await client.update_profile(first_name=bot_data["original_name"])
            break
        except Exception: await asyncio.sleep(60)

@app.on_message(filters.command("clock", prefixes=".") & filters.me)
async def toggle_clock(client, message):
    bot_data["clock"] = not bot_data["clock"]
    if bot_data["clock"]:
        bot_data["clock_task"] = asyncio.create_task(clock_loop(client))
        await message.edit_text("⏰ **ساعت فعال شد.**")
    else:
        if bot_data["clock_task"]: bot_data["clock_task"].cancel()
        await message.edit_text("⏰ **ساعت خاموش شد.**")

@app.on_message(filters.command("clockstyle", prefixes=".") & filters.me)
async def set_clockstyle(client, message):
    args = message.text.split()
    if len(args) > 1 and args[1].isdigit() and int(args[1]) in [1, 2, 3, 4]:
        bot_data["clock_style"] = int(args[1])
        await message.edit_text(f"🎨 **استایل ساعت {args[1]} شد.**")

@app.on_message(filters.command("afk", prefixes=".") & filters.me)
async def set_afk(client, message):
    bot_data["afk"] = True
    bot_data["afk_reason"] = message.text.split(maxsplit=1)[1] if len(message.text.split()) > 1 else "ثبت نشده"
    await message.edit_text(f"🌙 **AFK فعال شد.**")

@app.on_message(filters.command("unafk", prefixes=".") & filters.me)
async def unset_afk(client, message):
    bot_data["afk"] = False
    await message.edit_text("☀️ **AFK خاموش شد.**")

@app.on_message(filters.command("pmbot", prefixes=".") & filters.me)
async def toggle_pmbot(client, message):
    args = message.text.split()
    if len(args) > 1:
        bot_data["pmbot"] = (args[1] == "on")
        await message.edit_text(f"🤖 **منشی پیوی {'فعال' if bot_data['pmbot'] else 'خاموش'} شد.**")

@app.on_message(filters.command("antidel", prefixes=".") & filters.me)
async def toggle_antidel(client, message):
    args = message.text.split()
    if len(args) > 1:
        bot_data["antidel"] = (args[1] == "on")
        await message.edit_text(f"🛡 **ضد پاکسازی {'فعال' if bot_data['antidel'] else 'خاموش'} شد.**")

@app.on_message(filters.private & ~filters.me & ~filters.bot, group=1)
async def pm_handler(client, message):
    if bot_data["afk"]: await message.reply_text(f"👋 **آنلاین نیستم.**\n📝 علت: {bot_data['afk_reason']}")
    elif bot_data["pmbot"]: await message.reply_text(bot_data["pmbot_text"])

@app.on_message(filters.command("del", prefixes=".") & filters.me)
async def delete_my_msgs(client, message):
    args = message.text.split()
    if len(args) > 1 and args[1].isdigit():
        await safe_delete(message)
        async for m in client.get_chat_history(message.chat.id, limit=int(args[1]) * 2):
            if m.from_user and m.from_user.is_self: await m.delete()

@app.on_message(filters.command("purge", prefixes=".") & filters.me)
async def purge_msgs(client, message):
    if message.reply_to_message:
        await client.delete_messages(message.chat.id, list(range(message.reply_to_message.id, message.id + 1)))

@app.on_message(filters.command("calc", prefixes=".") & filters.me)
async def calculate(client, message):
    expr = message.text.split(maxsplit=1)
    if len(expr) > 1:
        try:
            clean_expr = re.sub(r'[^0-9\+\-\*\/\(\)\.]', '', expr[1])
            res = eval(clean_expr)
            await message.edit_text(f"🔢 **نتیجه:** `{res}`")
        except Exception:
            await message.edit_text("❌ **معادل نامعتبر.**")

@app.on_message(filters.command("type", prefixes=".") & filters.me)
async def typewriter(client, message):
    text = message.text.split(maxsplit=1)[1] if len(message.text.split()) > 1 else ""
    t = ""
    for c in text:
        t += c
        await message.edit_text(f"{t}▒")
        await asyncio.sleep(0.1)
    await message.edit_text(t)

@app.on_message(filters.command("font", prefixes=".") & filters.me)
async def font_style(client, message):
    text = message.text.split(maxsplit=1)[1] if len(message.text.split()) > 1 else ""
    await message.edit_text(text.translate(str.maketrans("abcdefghijklmnopqrstuvwxyz", "𝕒𝕓𝕔𝕕𝕖𝕗𝕘𝕙𝕚𝕛𝕜𝕝𝕞𝕟𝕠𝕡𝕢𝕣𝕤𝕥𝕦𝕧𝕨𝕩𝕪𝕫")))

@app.on_message(filters.command("info", prefixes=".") & filters.me)
async def user_info(client, message):
    target = message.reply_to_message.from_user if message.reply_to_message else message.from_user
    await message.edit_text(f"👤 **نام:** {target.first_name}\n🆔 **آیدی عددی:** `{target.id}`\n🌐 **نام کاربری:** @{target.username or 'ندارد'}")

@app.on_message(filters.command("ping", prefixes=".") & filters.me)
async def ping(client, message):
    start = datetime.now()
    await message.edit_text("🏓 **Pinging...**")
    end = datetime.now()
    await message.edit_text(f"🚀 **پینگ:** `{(end - start).microseconds // 1000}ms`")

if __name__ == "__main__":
    app.run()
