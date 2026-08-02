import asyncio
import os
import re
import sys
from datetime import datetime
from pytz import timezone
from pyrogram import Client, filters, idle
from pyrogram.types import Message

# ==================== CONFIGURATION ====================
API_ID = int(os.getenv("API_ID", "6"))
API_HASH = os.getenv("API_HASH", "eb06d4abfb49dc3eeb1aeb98ae0f581e")
SESSION_STRING = os.getenv("SESSION_STRING", "")

if not SESSION_STRING:
    print("❌ ERROR: SESSION_STRING missing in Secrets!")
    sys.exit(1)

app = Client(
    "my_selfbot",
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=SESSION_STRING,
    in_memory=True,
    sleep_threshold=30
)

# ==================== STATE MANAGEMENT ====================
STATE = {
    "clock": False,
    "clock_style": 1,
    "original_name": "",
    "afk": False,
    "afk_reason": "",
    "pm_bot": False,
    "pm_text": "سلام! در حال حاضر پاسخگو نیستم. لطفاً پیام بگذارید.",
    "anti_delete": True,
    "rdice": False,
    "rdice_target": "even",
    "rslot": False,
    "rbasket": False,
    "rbasket_target": 5,
    "rbowl": False,
    "rbowl_target": 6,
    "reroll_delay": 0.25,
    "loops": {},
    "schedules": [],
    "notes": {},
    "tagging": {},
    "saved_tags": []
}

CLOCK_STYLES = {
    1: ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9"],
    2: ["۰", "۱", "۲", "۳", "۴", "۵", "۶", "۷", "۸", "۹"],
    3: ["⓿", "❶", "❷", "❸", "❹", "❺", "❻", "❼", "❽", "❾"],
    4: ["𝟢", "𝟣", "𝟤", "𝟥", "𝟦", "𝟧", "𝟦", "𝟩", "𝟪", "𝟫"]
}

# ==================== HELPER FUNCTIONS ====================
def get_styled_time(style_num):
    tz = timezone('Asia/Tehran')
    now = datetime.now(tz).strftime("%H:%M")
    digits = CLOCK_STYLES.get(style_num, CLOCK_STYLES[1])
    styled = ""
    for char in now:
        if char.isdigit():
            styled += digits[int(char)]
        else:
            styled += char
    return styled

def clean_name_from_clock(name):
    if not name:
        return "User"
    cleaned = re.sub(r"\s*\|\s*[\d۰-۹⓿-❾𝟢-𝟫]+[:\s]+[\d۰-۹⓿-❾𝟢-𝟫]+", "", name)
    return cleaned.strip() or "User"

def get_dashboard_text(name):
    clock_st = f"🟢 فعال | استایل {STATE['clock_style']}" if STATE["clock"] else f"🔴 خاموش | استایل {STATE['clock_style']}"
    afk_st = f"🟢 فعال ({STATE['afk_reason']})" if STATE["afk"] else "🔴 خاموش"
    anti_del_st = "🟢 فعال" if STATE["anti_delete"] else "🔴 خاموش"
    pm_st = "🟢 فعال" if STATE["pm_bot"] else "🔴 خاموش"
    dice_st = f"🟢 روشن ({STATE['rdice_target']})" if STATE["rdice"] else "🔴 خاموش"
    slot_st = "🟢 روشن (هدف: ۷۷۷)" if STATE["rslot"] else "🔴 خاموش"
    basket_st = f"🟢 روشن (هدف: {STATE['rbasket_target']})" if STATE["rbasket"] else "🔴 خاموش"
    bowl_st = f"🟢 روشن (هدف: {STATE['rbowl_target']})" if STATE["rbowl"] else "🔴 خاموش"
    tags_count = len(STATE["saved_tags"])

    clean_first_name = clean_name_from_clock(name)

    return f"""📋 **داشبورد سلف‌بات اختصاصی {clean_first_name}**
━━━━━━━━━━━━━━━━━━━━
⏰ **ساعت اسم:** [ {clock_st} ]
🌙 **حالت AFK:** [ {afk_st} ]
🛡 **ضد پاکسازی:** [ {anti_del_st} ]
🤖 **منشی پیوی:** [ {pm_st} ]
🏷 **تگ‌های ثبت‌شده:** [ `{tags_count}` عدد ]
🎲 **تاس شانس:** [ {dice_st} ]
🎰 **اسلات شانس:** [ {slot_st} ]
🏀 **بسکتبال:** [ {basket_st} ]
🎳 **بولینگ:** [ {bowl_st} ]
⏱ **سرعت پرتاب:** [ `{STATE['reroll_delay']}` ثانیه ]
━━━━━━━━━━━━━━━━━━━━

🛠 **لیست کامل دستورات:**

🏷 **تگ‌ها و فراخوانی:**
• `.tags` ➔ مشاهده تگ‌هایی که شده‌اید
• `.cleartags` ➔ پاک کردن تاریخچه تگ‌ها
• `.tag [پیام]` ➔ تگ تکی اعضا
• `.all [پیام]` ➔ تگ ۵تایی اعضا
• `.tagfast [پیام]` ➔ تگ پرسرعت
• `.stoptag` ➔ توقف تگ اعضا

🎲🎰 **تاس و بازی‌های هوشمند:**
• `.rdice on [even/odd/1-6]` ➔ روشن کردن تاس
• `.rdice off` ➔ خاموش کردن تاس
• `.rslot on` ➔ روشن کردن اسلات
• `.rslot off` ➔ خاموش کردن اسلات
• `.rbasket on [1-5]` ➔ روشن کردن بسکتبال
• `.rbasket off` ➔ خاموش کردن بسکتبال
• `.rbowl on [1-6]` ➔ روشن کردن بولینگ
• `.rbowl off` ➔ خاموش کردن بولینگ
• `.rdelay [ثانیه]` ➔ تنظیم سرعت پرتاب

⚡️ **مدیریت حساب و سیستم:**
• `.clock` / `.clockstyle [1-4]` ➔ ساعت اسم
• `.afk [دلیل]` / `.unafk` ➔ حالت غیبت
• `.pmbot on/off` ➔ منشی پیوی
• `.antidel on/off` ➔ ضد پاکسازی

🔄 **زمان‌بندی و ابزارها:**
• `.loop [ID/here] [ثانیه] [متن]` ➔ ارسال تکراری
• `.stoploop` ➔ توقف تمام ارسال‌ها
• `.del [تعداد]` / `.purge` ➔ پاکسازی پیام
• `.calc` / `.type` / `.font` / `.info` / `.ping`"""

# ==================== BACKGROUND TASKS ====================
async def background_tasks():
    last_time = ""
    while True:
        try:
            if STATE["clock"]:
                time_str = get_styled_time(STATE["clock_style"])
                if time_str != last_time:
                    base_name = STATE["original_name"]
                    new_name = f"{base_name} | {time_str}"
                    await app.update_profile(first_name=new_name)
                    last_time = time_str
            
            tz = timezone('Asia/Tehran')
            now_hm = datetime.now(tz).strftime("%H:%M")
            to_remove = []
            for item in STATE["schedules"]:
                if item["time"] == now_hm:
                    await app.send_message(item["chat_id"], item["text"])
                    to_remove.append(item)
            for r in to_remove:
                STATE["schedules"].remove(r)

            await asyncio.sleep(10)
        except Exception:
            await asyncio.sleep(15)

# ==================== MENTION / TAG LOGGER ====================
@app.on_message(filters.mentioned & ~filters.me)
async def log_mentions(client, message: Message):
    try:
        chat_title = message.chat.title if message.chat.title else "چت خصوصی/گروه"
        sender = message.from_user.first_name if message.from_user else "ناشناس"
        msg_link = message.link if message.link else "بدون لینک"
        tz = timezone('Asia/Tehran')
        time_now = datetime.now(tz).strftime("%H:%M:%S")

        tag_info = {
            "sender": sender,
            "chat": chat_title,
            "text": message.text or "[رسانه/استیکر]",
            "link": msg_link,
            "time": time_now
        }
        STATE["saved_tags"].append(tag_info)
    except Exception:
        pass

@app.on_message(filters.me & filters.command("tags", prefixes="."))
async def show_tags(client, message: Message):
    if not STATE["saved_tags"]:
        await message.edit_text("🏷 **هیچ تگی ثبت نشده است.**")
        return
    
    text = f"🏷 **لیست آخرین تگ‌های شما ({len(STATE['saved_tags'])} مورد):**\n━━━━━━━━━━━━━━━━━━━━\n"
    for idx, t in enumerate(STATE["saved_tags"][-10:], 1):
        text += f"{idx}. **ارسال‌کننده:** {t['sender']}\n📍 **گروه:** {t['chat']}\n⏰ **ساعت:** `{t['time']}`\n💬 **متن:** {t['text'][:30]}\n🔗 [مشاهده پیام]({t['link']})\n━━━━━━━━━━━━━━━━━━━━\n"
    
    await message.edit_text(text, disable_web_page_preview=True)

@app.on_message(filters.me & filters.command("cleartags", prefixes="."))
async def clear_tags(client, message: Message):
    STATE["saved_tags"].clear()
    await message.edit_text("🧹 **تاریخچه تگ‌ها با موفقیت پاک شد.**")

# ==================== TAGGING MEMBERS SYSTEM ====================
@app.on_message(filters.me & filters.command(["tag", "all", "tagfast"], prefixes="."))
async def start_tagging(client, message: Message):
    chat_id = message.chat.id
    cmd = message.command[0].lower()
    custom_msg = " ".join(message.command[1:]) if len(message.command) > 1 else ""

    STATE["tagging"][chat_id] = True
    await message.delete()

    members = []
    async for member in client.get_chat_members(chat_id):
        if not member.user.is_bot and not member.user.is_deleted:
            members.append(member.user)

    if cmd == "tag":
        for user in members:
            if not STATE["tagging"].get(chat_id, False): break
            mention = f"[{user.first_name}](tg://user?id={user.id})"
            text = f"{mention} {custom_msg}".strip()
            await client.send_message(chat_id, text)
            await asyncio.sleep(1.5)

    elif cmd == "all":
        chunk_size = 5
        for i in range(0, len(members), chunk_size):
            if not STATE["tagging"].get(chat_id, False): break
            chunk = members[i:i + chunk_size]
            mentions = " ".join([f"[{u.first_name}](tg://user?id={u.id})" for u in chunk])
            text = f"{mentions}\n{custom_msg}".strip()
            await client.send_message(chat_id, text)
            await asyncio.sleep(2.5)

    elif cmd == "tagfast":
        chunk_size = 5
        for i in range(0, len(members), chunk_size):
            if not STATE["tagging"].get(chat_id, False): break
            chunk = members[i:i + chunk_size]
            mentions = " ".join([f"[{u.first_name}](tg://user?id={u.id})" for u in chunk])
            text = f"{mentions}\n{custom_msg}".strip()
            await client.send_message(chat_id, text)
            await asyncio.sleep(0.3)

    STATE["tagging"][chat_id] = False

@app.on_message(filters.me & filters.command("stoptag", prefixes="."))
async def stop_tagging(client, message: Message):
    chat_id = message.chat.id
    STATE["tagging"][chat_id] = False
    await message.edit_text("🛑 **تگ کردن اعضا متوقف شد.**")

# ==================== HANDLERS & COMMANDS ====================
@app.on_message(filters.me & filters.command(["panel", "help"], prefixes="."))
async def show_panel(client, message: Message):
    me = await client.get_me()
    await message.edit_text(get_dashboard_text(me.first_name))

@app.on_message(filters.me & filters.command("ping", prefixes="."))
async def ping_handler(client, message: Message):
    start = datetime.now()
    reply = await message.edit_text("🚀 در حال بررسی...")
    end = datetime.now()
    ms = (end - start).microseconds / 1000
    await reply.edit_text(f"⚡️ **سلف‌بات فعال است!**\nپینگ: `{ms:.1f}ms`")

# --- CLOCK & AFK & PMBOT & ANTIDEL ---
@app.on_message(filters.me & filters.command("clock", prefixes="."))
async def toggle_clock(client, message: Message):
    STATE["clock"] = not STATE["clock"]
    st = "روشن 🟢" if STATE["clock"] else "خاموش 🔴"
    if not STATE["clock"]:
        await app.update_profile(first_name=STATE["original_name"])
    await message.edit_text(f"⏰ **ساعت اسم:** {st}")

@app.on_message(filters.me & filters.command("clockstyle", prefixes="."))
async def change_clock_style(client, message: Message):
    try:
        style = int(message.command[1])
        if style in CLOCK_STYLES:
            STATE["clock_style"] = style
            await message.edit_text(f"🎨 **استایل ساعت به {style} تغییر یافت.**")
        else:
            await message.edit_text("❌ استایل معتبر نیست (1 تا 4).")
    except Exception:
        await message.edit_text("❌ فرمت صحیح: `.clockstyle 1`")

@app.on_message(filters.me & filters.command("afk", prefixes="."))
async def set_afk(client, message: Message):
    reason = " ".join(message.command[1:]) if len(message.command) > 1 else "ثبت نشده"
    STATE["afk"] = True
    STATE["afk_reason"] = reason
    await message.edit_text(f"🌙 **حالت غیبت (AFK) فعال شد.**\nدلیل: `{reason}`")

@app.on_message(filters.me & filters.command("unafk", prefixes="."))
async def unset_afk(client, message: Message):
    STATE["afk"] = False
    await message.edit_text("☀️ **حالت غیبت (AFK) غیرفعال شد.**")

@app.on_message(filters.me & filters.command("pmbot", prefixes="."))
async def toggle_pmbot(client, message: Message):
    if len(message.command) > 1 and message.command[1].lower() == "on":
        STATE["pm_bot"] = True
        await message.edit_text("🤖 **منشی پیوی روشن شد 🟢**")
    else:
        STATE["pm_bot"] = False
        await message.edit_text("🤖 **منشی پیوی خاموش شد 🔴**")

@app.on_message(filters.me & filters.command("antidel", prefixes="."))
async def toggle_antidel(client, message: Message):
    if len(message.command) > 1 and message.command[1].lower() == "off":
        STATE["anti_delete"] = False
        await message.edit_text("🛡 **ضد پاکسازی خاموش شد 🔴**")
    else:
        STATE["anti_delete"] = True
        await message.edit_text("🛡 **ضد پاکسازی روشن شد 🟢**")

# --- GAME BOT TOGGLES & SPEED ---
@app.on_message(filters.me & filters.command("rdelay", prefixes="."))
async def set_reroll_delay(client, message: Message):
    try:
        delay = float(message.command[1])
        if delay < 0.05:
            await message.edit_text("⚠️ تاخیر خیلی کم ممکن است باعث مسدود شدن توسط تلگرام شود.")
            return
        STATE["reroll_delay"] = delay
        await message.edit_text(f"⏱ **تاخیر پرتاب‌ها روی `{delay}` ثانیه تنظیم شد.**")
    except Exception:
        await message.edit_text("❌ فرمت صحیح: `.rdelay 0.2`")

@app.on_message(filters.me & filters.command("rdice", prefixes="."))
async def toggle_rdice(client, message: Message):
    if len(message.command) > 1 and message.command[1].lower() == "on":
        STATE["rdice"] = True
        target = message.command[2] if len(message.command) > 2 else "even"
        STATE["rdice_target"] = target
        await message.edit_text(f"🎲 **تاس روشن شد 🟢 (هدف: {target})**")
    else:
        STATE["rdice"] = False
        await message.edit_text("🎲 **تاس خاموش شد 🔴**")

@app.on_message(filters.me & filters.command("rslot", prefixes="."))
async def toggle_rslot(client, message: Message):
    if len(message.command) > 1 and message.command[1].lower() == "on":
        STATE["rslot"] = True
        await message.edit_text("🎰 **اسلات روشن شد 🟢 (هدف: ۷۷۷)**")
    else:
        STATE["rslot"] = False
        await message.edit_text("🎰 **اسلات خاموش شد 🔴**")

@app.on_message(filters.me & filters.command("rbasket", prefixes="."))
async def toggle_rbasket(client, message: Message):
    if len(message.command) > 1 and message.command[1].lower() == "on":
        STATE["rbasket"] = True
        target = int(message.command[2]) if len(message.command) > 2 else 5
        STATE["rbasket_target"] = target
        await message.edit_text(f"🏀 **بسکتبال روشن شد 🟢 (هدف: {target})**")
    else:
        STATE["rbasket"] = False
        await message.edit_text("🏀 **بسکتبال خاموش شد 🔴**")

@app.on_message(filters.me & filters.command("rbowl", prefixes="."))
async def toggle_rbowl(client, message: Message):
    if len(message.command) > 1 and message.command[1].lower() == "on":
        STATE["rbowl"] = True
        target = int(message.command[2]) if len(message.command) > 2 else 6
        STATE["rbowl_target"] = target
        await message.edit_text(f"🎳 **بولینگ روشن شد 🟢 (هدف: {target})**")
    else:
        STATE["rbowl"] = False
        await message.edit_text("🎳 **بولینگ خاموش شد 🔴**")

# --- HIGH-SPEED AUTOMATIC REROLL HANDLER ---
@app.on_message(filters.me & filters.dice)
async def handle_dice_reroll(client, message: Message):
    emoji = message.dice.emoji
    val = message.dice.value
    chat_id = message.chat.id

    is_target_active = False
    matched = False

    if STATE["rdice"] and emoji == "🎲":
        is_target_active = True
        target = STATE["rdice_target"]
        if target == "even" and val % 2 == 0: matched = True
        elif target == "odd" and val % 2 != 0: matched = True
        elif target.isdigit() and int(target) == val: matched = True

    elif STATE["rslot"] and emoji == "🎰":
        is_target_active = True
        if val == 64: matched = True

    elif STATE["rbasket"] and emoji == "🏀":
        is_target_active = True
        if val == STATE["rbasket_target"]: matched = True

    elif STATE["rbowl"] and emoji == "🎳":
        is_target_active = True
        if val == STATE["rbowl_target"]: matched = True

    if is_target_active and not matched:
        try:
            await asyncio.sleep(STATE["reroll_delay"])
            await message.delete()
            await client.send_dice(chat_id, emoji=emoji)
        except Exception:
            pass

# --- LOOPS & SCHEDULE ---
@app.on_message(filters.me & filters.command("loop", prefixes="."))
async def start_loop(client, message: Message):
    try:
        raw_target = message.command[1]
        delay = int(message.command[2])
        text = " ".join(message.command[3:])
        
        target_chat_id = message.chat.id if raw_target.lower() == "here" else int(raw_target)
        
        async def loop_worker():
            while True:
                await client.send_message(target_chat_id, text)
                await asyncio.sleep(delay)
                
        task = asyncio.create_task(loop_worker())
        loop_id = len(STATE["loops"]) + 1
        STATE["loops"][loop_id] = task
        
        await message.edit_text(
            f"🔄 ارسال تکراری فعال شد!\n"
            f"🎯 به: {target_chat_id}\n"
            f"⏱ هر {delay} ثانیه"
        )
    except Exception:
        await message.edit_text("❌ فرمت: `.loop [here/آیدی_چت] [ثانیه] [متن]`")

@app.on_message(filters.me & filters.command("loops", prefixes="."))
async def list_loops(client, message: Message):
    if not STATE["loops"]:
        await message.edit_text("🔄 هیچ حلقه ارسالی فعال نیست.")
        return
    await message.edit_text(f"🔄 **تعداد حلقه‌های فعال:** `{len(STATE['loops'])}` عدد")

@app.on_message(filters.me & filters.command("stoploop", prefixes="."))
async def stop_loops(client, message: Message):
    for t in STATE["loops"].values():
        t.cancel()
    STATE["loops"].clear()
    await message.edit_text("🛑 **تمام ارسال‌های تکراری متوقف شدند.**")

@app.on_message(filters.me & filters.command("schedule", prefixes="."))
async def schedule_msg(client, message: Message):
    try:
        time_str = message.command[1]
        text = " ".join(message.command[2:])
        STATE["schedules"].append({"chat_id": message.chat.id, "time": time_str, "text": text})
        await message.edit_text(f"⏰ **پیام برای ساعت {time_str} زمان‌بندی شد.**")
    except Exception:
        await message.edit_text("❌ فرمت: `.schedule 14:30 متن پیام`")

# --- UTILS & EXTRA COMMANDS ---
@app.on_message(filters.me & filters.command("del", prefixes="."))
async def delete_my_messages(client, message: Message):
    try:
        count = int(message.command[1])
        async for msg in client.get_chat_history(message.chat.id, limit=count + 1):
            if msg.from_user and msg.from_user.is_self:
                await msg.delete()
    except Exception:
        await message.edit_text("❌ فرمت: `.del 10`")

@app.on_message(filters.me & filters.command("purge", prefixes="."))
async def purge_messages(client, message: Message):
    if not message.reply_to_message:
        await message.edit_text("❌ روی یک پیام ریپلای کن.")
        return
    start_id = message.reply_to_message.id
    end_id = message.id
    msg_ids = list(range(start_id, end_id + 1))
    for i in range(0, len(msg_ids), 100):
        await client.delete_messages(message.chat.id, msg_ids[i:i+100])

@app.on_message(filters.me & filters.command("calc", prefixes="."))
async def calculator(client, message: Message):
    try:
        expr = " ".join(message.command[1:])
        res = eval(expr, {"__builtins__": None}, {})
        await message.edit_text(f"🧮 **نتیجه:** `{res}`")
    except Exception:
        await message.edit_text("❌ عبارت ریاضی نامعتبر است.")

@app.on_message(filters.me & filters.command("type", prefixes="."))
async def typewriter(client, message: Message):
    text = " ".join(message.command[1:])
    typed = ""
    for char in text:
        typed += char
        await message.edit_text(typed + "▒")
        await asyncio.sleep(0.02)
    await message.edit_text(typed)

@app.on_message(filters.me & filters.command("font", prefixes="."))
async def make_font(client, message: Message):
    if len(message.command) < 2:
        await message.edit_text("❌ متن را وارد کن.")
        return
    text = " ".join(message.command[1:])
    src = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
    dst = "𝒶𝒷𝒸𝒹ℯ𝒻ℊ𝒽𝒾𝒿𝓀𝓁𝓂𝓃ℴ𝓅𝓆𝓇𝓈𝓉𝓊𝓋𝓌𝓍𝓎𝓏𝒜ℬ𝒞𝒟ℰℱ𝒢ℋℐ𝒥𝒦ℒℳ𝒩𝒪𝒫𝒬ℛ𝒮𝒯𝒰𝒱𝒲𝒳𝒴𝒵"
    f1 = text.translate(str.maketrans(src, dst))
    await message.edit_text(f"فونت:\n`{f1}`")

@app.on_message(filters.me & filters.command("save", prefixes="."))
async def save_note(client, message: Message):
    if len(message.command) < 2 or not message.reply_to_message:
        await message.edit_text("❌ روی یک پیام ریپلای کن و اسم بگذار.")
        return
    name = message.command[1]
    STATE["notes"][name] = message.reply_to_message.id
    await message.edit_text(f"💾 پیام با نام `{name}` ذخیره شد.")

@app.on_message(filters.me & filters.command("get", prefixes="."))
async def get_note(client, message: Message):
    if len(message.command) < 2:
        await message.edit_text("❌ نام را وارد کن.")
        return
    name = message.command[1]
    if name in STATE["notes"]:
        msg_id = STATE["notes"][name]
        await client.forward_messages(message.chat.id, message.chat.id, msg_id)
    else:
        await message.edit_text("❌ نام پیدا نشد.")

@app.on_message(filters.me & filters.command("info", prefixes="."))
async def get_info(client, message: Message):
    target = message.reply_to_message.from_user if message.reply_to_message else message.from_user
    await message.edit_text(
        f"👤 **نام:** {target.first_name}\n"
        f"🆔 **آیدی:** `{target.id}`\n"
        f"یوزرنیم: @{target.username if target.username else 'ندارد'}"
    )

# --- RESPONDERS ---
@app.on_message(filters.private & ~filters.me)
async def pm_handler(client, message: Message):
    if STATE["afk"]:
        await message.reply_text(f"🌙 **صاحب اکانت غایب است.**\nدلیل: `{STATE['afk_reason']}`")
    elif STATE["pm_bot"]:
        await message.reply_text(STATE["pm_text"])

# ==================== START BOT ====================
async def main():
    await app.start()
    me = await app.get_me()
    STATE["original_name"] = clean_name_from_clock(me.first_name)
    asyncio.create_task(background_tasks())
    print(f"✅ Selfbot Started as {STATE['original_name']}")
    await idle()
    await app.stop()

if __name__ == "__main__":
    app.run(main())
