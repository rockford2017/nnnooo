import asyncio
import os
import re
import sys
from datetime import datetime
from pytz import timezone
from pyrogram import Client, filters, idle
from pyrogram.types import Message, User

try:
    import eval_utils
except ImportError:
    eval_utils = None

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
    "loops": {},
    "schedules": [],
    "tags": {},
    "notes": {},
    "deleted_msgs_log": {}
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

def get_dashboard_text(name):
    clock_st = f"🟢 فعال | استایل {STATE['clock_style']}" if STATE["clock"] else f"🔴 خاموش | استایل {STATE['clock_style']}"
    afk_st = f"🟢 فعال ({STATE['afk_reason']})" if STATE["afk"] else "🔴 خاموش"
    anti_del_st = "🟢 فعال" if STATE["anti_delete"] else "🔴 خاموش"
    pm_st = "🟢 فعال" if STATE["pm_bot"] else "🔴 خاموش"
    dice_st = f"🟢 روشن ({STATE['rdice_target']})" if STATE["rdice"] else "🔴 خاموش"
    slot_st = "🟢 روشن (هدف: 64)" if STATE["rslot"] else "🔴 خاموش"

    return f"""📋 **داشبورد سلف‌بات اختصاصی {name}**
━━━━━━━━━━━━━━━━━━━━
⏰ **ساعت اسم:** [ {clock_st} ]
🌙 **حالت AFK:** [ {afk_st} ]
🛡 **ضد پاکسازی:** [ {anti_del_st} ]
🤖 **منشی پیوی:** [ {pm_st} ]
🎲 **تاس شانس:** [ {dice_st} ]
🎰 **اسلات شانس:** [ {slot_st} ]
━━━━━━━━━━━━━━━━━━━━

🛠 **لیست کامل دستورات:**

🎲🎰 **تاس و اسلات هوشمند:**
• `.rdice on [even/odd/1-6]` ➔ روشن کردن تاس هوشمند
• `.rdice off` ➔ خاموش کردن تاس
• `.rslot on` ➔ روشن کردن اسلات (هدف: ۷۷۷)
• `.rslot off` ➔ خاموش کردن اسلات

⚡️ **مدیریت حساب و سیستم:**
• `.clock` ➔ روشن/خاموش کردن ساعت اسم
• `.clockstyle [1-4]` ➔ تغییر فونت ساعت اسم
• `.afk [دلیل]` / `.unafk` ➔ حالت غیبت خودکار
• `.pmbot on/off` ➔ فعال/غیرفعال‌سازی منشی پیوی
• `.antidel on/off` ➔ مدیریت سیستم ضد پاکسازی

🔄 **زمان‌بندی و ارسال انبوه:**
• `.loop [ID/here] [ثانیه] [متن]` ➔ ارسال تکراری (گزارش به سیو مسج)
• `.loops` ➔ مشاهده حلقه‌های فعال
• `.stoploop` ➔ متوقف کردن تمام ارسال‌های تکراری
• `.schedule [HH:MM] [متن]` ➔ ارسال پیام سر ساعت مشخص

🌐 **ابزارها و مدیریت چت:**
• `.del [تعداد]` ➔ پاکسازی پیام‌های خودتان
• `.purge` ➔ پاکسازی پیام‌ها تا پیام ریپلای‌شده
• `.mute` / `.unmute` ➔ سکوت کاربر در چت (ریپلای)
• `.calc [عبارت]` ➔ ماشین حساب سریع
• `.tags` ➔ مشاهده لیست منشن‌ها/تگ‌های ذخیره‌شده
• `.save [نام]` / `.get [نام]` ➔ ذخیره و فراخوانی نوت
• `.type [متن]` ➔ تایپ متحرک با بالاترین سرعت
• `.font [متن]` ➔ ساخت فونت انگلیسی فانتزی
• `.info` ➔ اطلاعات جامع چت/کاربر
• `.ping` ➔ بررسی پینگ و اتصال سلف‌بات"""

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

            await asyncio.sleep(15)
        except Exception:
            await asyncio.sleep(20)

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
    await reply.edit_text(f"⚡️ **سلف‌بات گیت‌هاب فعال است!**\nپینگ: `{ms:.1f}ms`")

# --- CLOCK & AFK & PMBOT & ANTIDEL ---
@app.on_message(filters.me & filters.command("clock", prefixes="."))
async def toggle_clock(client, message: Message):
    STATE["clock"] = not STATE["clock"]
    st = "روشن 🟢" if STATE["clock"] else "خاموش 🔴"
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
        
        report_text = (
            f"🔄 ارسال تکراری فعال شد!\n"
            f"🎯 به: {target_chat_id}\n"
            f"⏱ هر {delay} ثانیه"
        )
        
        await client.send_message("me", report_text)
        await message.delete()

    except Exception as e:
        await message.edit_text(f"❌ فرمت نادرست است.\nنمونه: `.loop here 246 متن پیام`\nخطا: `{e}`")

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

# --- GAME BOT REROLL HANDLERS ---
@app.on_message(filters.me & filters.command("rdice", prefixes="."))
async def toggle_rdice(client, message: Message):
    if len(message.command) > 1 and message.command[1].lower() == "on":
        STATE["rdice"] = True
        target = message.command[2] if len(message.command) > 2 else "even"
        STATE["rdice_target"] = target
        await message.edit_text(f"🎲 **تاس هوشمند روشن شد 🟢 (هدف: {target})**")
    else:
        STATE["rdice"] = False
        await message.edit_text("🎲 **تاس هوشمند خاموش شد 🔴**")

@app.on_message(filters.me & filters.command("rslot", prefixes="."))
async def toggle_rslot(client, message: Message):
    if len(message.command) > 1 and message.command[1].lower() == "on":
        STATE["rslot"] = True
        await message.edit_text("🎰 **اسلات هوشمند روشن شد 🟢 (هدف: 64)**")
    else:
        STATE["rslot"] = False
        await message.edit_text("🎰 **اسلات هوشمند خاموش شد 🔴**")

@app.on_message(filters.me & filters.dice)
async def handle_dice_reroll(client, message: Message):
    if STATE["rdice"] and message.dice.emoji == "🎲":
        val = message.dice.value
        target = STATE["rdice_target"]
        matched = False
        if target == "even" and val % 2 == 0: matched = True
        elif target == "odd" and val % 2 != 0: matched = True
        elif target.isdigit() and int(target) == val: matched = True

        if not matched:
            await message.delete()
            await client.send_dice(message.chat.id, emoji="🎲")

    elif STATE["rslot"] and message.dice.emoji == "🎰":
        if message.dice.value != 64:
            await message.delete()
            await client.send_dice(message.chat.id, emoji="🎰")

# --- UTILS (DELETE, PURGE, CALC, TYPE, FONT, SAVE, INFO) ---
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
        await message.edit_text("❌ روی پیامی که می‌خواهی پاکسازی از آنجا شروع شود ریپلای کن.")
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
        await message.edit_text("❌ متن مورد نظر را وارد کن.")
        return
    text = " ".join(message.command[1:])
    f1 = text.translate(str.maketrans("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ", "𝒶𝒷𝒸𝒹ℯ𝒻ℊ𝒽𝒾𝒿𝓀𝓁𝓂𝓃ℴ𝓅𝓆𝓇𝓈𝓉𝓊𝓋𝓌𝓍𝓎𝓏𝒜ℬ𝒞𝒟ℰℱ𝒢ℋℐ𝒥𝒦ℒℳ𝒩𝒪𝒫𝒬ℛ𝒮𝒯𝒰𝒱𝒲𝒳𝒴𝒵"))
    f2 = text.translate(str.maketrans("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ", "𝕒𝕓𝕔𝕕𝕖𝕗𝕘𝕙𝕚𝕛𝕜𝕝𝕞𝕟𝕠𝕡𝕢𝕣𝕤𝕥𝕦𝕧𝕨𝕩𝕪𝕫𝔸𝔹ℂ𝔻𝔼𝔽𝔾ℍ𝕀𝕁𝕂𝕃𝕄ℕ𝕆ℙℚℝ𝕊𝕋𝕌𝕍𝕎𝕏𝕐ℤ"))
    await message.edit_text(f"فونت ۱:\n`{f1}`\n\nفونت ۲:\n`{f2}`")

@app.on_message(filters.me & filters.command("save", prefixes="."))
async def save_note(client, message: Message):
    if len(message.command) < 2 or not message.reply_to_message:
        await message.edit_text("❌ روی یک پیام ریپلای کن و اسم بذار: `.save mynote`")
        return
    name = message.command[1]
    STATE["notes"][name] = message.reply_to_message.id
    await message.edit_text(f"💾 پیام با نام `{name}` ذخیره شد.")

@app.on_message(filters.me & filters.command("get", prefixes="."))
async def get_note(client, message: Message):
    if len(message.command) < 2:
        await message.edit_text("❌ نام ذخیره‌شده را وارد کن.")
        return
    name = message.command[1]
    if name in STATE["notes"]:
        msg_id = STATE["notes"][name]
        await client.forward_messages(message.chat.id, message.chat.id, msg_id)
    else:
        await message.edit_text("❌ این نام پیدا نشد.")

@app.on_message(filters.me & filters.command("info", prefixes="."))
async def get_info(client, message: Message):
    target = message.reply_to_message.from_user if message.reply_to_message else message.from_user
    await message.edit_text(
        f"👤 **نام:** {target.first_name}\n"
        f"🆔 **آیدی عددی:** `{target.id}`\n"
        f"UserName: @{target.username if target.username else 'ندارد'}"
    )

# --- AUTO PM RESPONDER & AFK RESPONDER ---
@app.on_message(filters.private & ~filters.me)
async def pm_handler(client, message: Message):
    if STATE["afk"]:
        await message.reply_text(f"🌙 **صاحب اکانت در حالت غیبت است.**\nدلیل: `{STATE['afk_reason']}`")
    elif STATE["pm_bot"]:
        await message.reply_text(STATE["pm_text"])

# ==================== START BOT ====================
async def main():
    await app.start()
    me = await app.get_me()
    STATE["original_name"] = me.first_name or "User"
    asyncio.create_task(background_tasks())
    print(f"✅ Selfbot Started as {me.first_name}")
    await idle()
    await app.stop()

if __name__ == "__main__":
    app.run(main())
