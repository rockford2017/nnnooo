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
    "deleted_msgs_log": {}
}

CLOCK_STYLES = {
    1: ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9"], # انگلیسی استاندارد
    2: ["۰", "۱", "۲", "۳", "۴", "۵", "۶", "۷", "۸", "۹"], # فارسی
    3: ["⓿", "❶", "❷", "❸", "❹", "❺", "❻", "❼", "❽", "❾"], # دایره‌ای
    4: ["𝟢", "𝟣", "𝟤", "𝟥", "𝟦", "𝟧", "𝟨", "𝟩", "𝟪", "𝟫"]  # ریاضی
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

🛠 **لیست دستورات کامل:**

🎲🎰 **تاس و اسلات پیشرفته:**
• `.rdice on [even/odd/1-6]` ➔ روشن کردن تاس هوشمند
• `.rdice off` ➔ خاموش کردن تاس
• `.rslot on` ➔ روشن کردن اسلات (۷۷۷)
• `.rslot off` ➔ خاموش کردن اسلات

⚡️ **مدیریت سیستم:**
• `.clock` ➔ روشن/خاموش کردن ساعت
• `.clockstyle [1-4]` ➔ تغییر استایل ساعت (1=انگلیسی)
• `.afk [دلیل]` / `.unafk` ➔ حالت غیبت
• `.pmbot on/off` ➔ پاسخگوی خودکار پیوی
• `.antidel on/off` ➔ مدیریت ضد پاکسازی

🔄 **زمان‌بندی و ارسال:**
• `.loop [ID/Here] [ثانیه] [متن]` ➔ ارسال تکراری
• `.loops` ➔ لیست ارسال‌های فعال
• `.stoploop` ➔ توقف تمام ارسال‌ها
• `.schedule [HH:MM] [متن]` ➔ ارسال سر ساعت

🌐 **ابزارهای کاربردی:**
• `.mute` / `.unmute` ➔ سکوت کاربر (ریپلای)
• `.purge` ➔ پاکسازی گروهی پیام‌ها
• `.calc [عبارت]` ➔ ماشین حساب
• `.tags` ➔ مشاهده منشن‌های ذخیره شده
• `.save [نام]` / `.get [نام]` ➔ ذخیره و دریافت پیام
• `.type [متن]` ➔ تایپ متحرک
• `.sticker` ➔ تبدیل عکس به استیکر (ریپلای)

🛠 **ابزارهای عمومی:**
• `.del [تعداد]` ➔ پاکسازی پیام خودت
• `.info` ➔ اطلاعات چت یا کاربر
• `.font [متن]` ➔ ساخت فونت انگلیسی زیبا
• `.ping` ➔ تست سرعت سلف‌بات"""

# ==================== BACKGROUND TASKS ====================
async def background_tasks():
    last_time = ""
    while True:
        try:
            # 1. Update Clock
            if STATE["clock"]:
                time_str = get_styled_time(STATE["clock_style"])
                if time_str != last_time:
                    base_name = STATE["original_name"]
                    new_name = f"{base_name} | {time_str}"
                    await app.update_profile(first_name=new_name)
                    last_time = time_str
            
            # 2. Check Scheduled Messages
            tz = timezone('Asia/Tehran')
            now_hm = datetime.now(tz).strftime("%H:%M")
            to_remove = []
            for item in STATE["schedules"]:
                if item["time"] == now_hm:
                    await app.send_message(item["chat_id"], item["text"])
                    to_remove.append(item)
            for r in to_remove:
                STATE["schedules"].remove(r)

            await asyncio.sleep(20)
        except Exception:
            await asyncio.sleep(25)

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

# --- CLOCK & AFK & PMBOT ---
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

# --- DICE & SLOT ---
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

# --- LOOPS & SCHEDULE ---
@app.on_message(filters.me & filters.command("loop", prefixes="."))
async def start_loop(client, message: Message):
    try:
        chat_id = message.chat.id if message.command[1].lower() == "here" else int(message.command[1])
        delay = int(message.command[2])
        text = " ".join(message.command[3:])
        
        async def loop_worker():
            while True:
                await client.send_message(chat_id, text)
                await asyncio.sleep(delay)
                
        task = asyncio.create_task(loop_worker())
        loop_id = len(STATE["loops"]) + 1
        STATE["loops"][loop_id] = task
        await message.edit_text(f"🔄 **ارسال تکراری شروع شد (کد حلقه: {loop_id})**")
    except Exception:
        await message.edit_text("❌ فرمت: `.loop [here/ID] [ثانیه] [متن]`")

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
    await message.edit_text("🛑 **تمام حلقه‌های ارسال متوقف شدند.**")

@app.on_message(filters.me & filters.command("schedule", prefixes="."))
async def schedule_msg(client, message: Message):
    try:
        time_str = message.command[1] # HH:MM
        text = " ".join(message.command[2:])
        STATE["schedules"].append({"chat_id": message.chat.id, "time": time_str, "text": text})
        await message.edit_text(f"⏰ **پیام برای ساعت {time_str} زمان‌بندی شد.**")
    except Exception:
        await message.edit_text("❌ فرمت: `.schedule 14:30 متن پیام`")

# --- UTILS (TYPE, FONT, STICKER, CALC, TAGS) ---
@app.on_message(filters.me & filters.command("type", prefixes="."))
async def typewriter(client, message: Message):
    text = " ".join(message.command[1:])
    typed = ""
    for char in text:
        typed += char
        await message.edit_text(typed + "▒")
        await asyncio.sleep(0.1)
    await message.edit_text(typed)

@app.on_message(filters.me & filters.command("font", prefixes="."))
async def make_font(client, message: Message):
    text = " ".join(message.command[1:])
    fonts = [
        text.translate(str.maketrans("abcdefghijklmnopqrstuvwxyz", "𝒶𝒷𝒸𝒹ℯ𝒻ℊ𝒽𝒾𝒿𝓀𝓁𝓂𝓃ℴ𝓅𝓆𝓇𝓈𝓉𝓊𝓋𝓌𝓍𝓎𝓏")),
        text.translate(str.maketrans("abcdefghijklmnopqrstuvwxyz", "𝕒𝕓𝕔𝕕𝕖𝕗𝕘𝕙𝕚𝕛𝕜𝕝𝕞𝕟𝕠𝕡𝕢𝕣𝕤𝕥𝕦𝕧𝕨𝕩𝕪𝕫")),
        text.translate(str.maketrans("abcdefghijklmnopqrstuvwxyz", "ⓐⓑⓒⓓⓔⓕⓖⓗⓘⓙⓚⓛⓜⓝⓞⓟⓠⓡⓢⓣⓤⓥⓦⓧⓨⓩ"))
    ]
    res = "\n\n".join(fonts)
    await message.edit_text(f"🎨 **فونت‌های ساخته شده:**\n\n{res}")

@app.on_message(filters.me & filters.command("sticker", prefixes="."))
async def photo_to_sticker(client, message: Message):
    if message.reply_to_message and message.reply_to_message.photo:
        await message.edit_text("⏳ در حال تبدیل به استیکر...")
        file_path = await client.download_media(message.reply_to_message)
        await client.send_sticker(message.chat.id, file_path)
        await message.delete()
        if os.path.exists(file_path):
            os.remove(file_path)
    else:
        await message.edit_text("❌ لطفاً روی یک عکس ریپلای کنید.")

@app.on_message(filters.me & filters.command("save", prefixes="."))
async def save_tag(client, message: Message):
    if not message.reply_to_message or len(message.command) < 2:
        await message.edit_text("❌ روی پیام ریپلای کنید و نام بذارید: `.save test`")
        return
    name = message.command[1]
    STATE["tags"][name] = message.reply_to_message.text or message.reply_to_message.caption or ""
    await message.edit_text(f"✅ پیام با نام `{name}` ذخیره شد.")

@app.on_message(filters.me & filters.command("get", prefixes="."))
async def get_tag(client, message: Message):
    if len(message.command) < 2 or message.command[1] not in STATE["tags"]:
        await message.edit_text("❌ نام معتبر وارد کنید.")
        return
    await message.edit_text(STATE["tags"][message.command[1]])

@app.on_message(filters.me & filters.command("tags", prefixes="."))
async def list_tags(client, message: Message):
    if not STATE["tags"]:
        await message.edit_text("📌 هیچ پیامی ذخیره نشده است.")
        return
    res = "\n".join([f"• `{k}`" for k in STATE["tags"].keys()])
    await message.edit_text(f"📌 **پیام‌های ذخیره شده:**\n{res}")

@app.on_message(filters.me & filters.command("calc", prefixes="."))
async def calculator(client, message: Message):
    try:
        expr = " ".join(message.command[1:])
        result = eval(expr)
        await message.edit_text(f"🧮 **محاسبه:** `{expr}`\n✅ **نتیجه:** `{result}`")
    except Exception:
        await message.edit_text("❌ عبارت ریاضی نامعتبر است.")

# --- MANAGEMENT (DEL, PURGE, MUTE, INFO) ---
@app.on_message(filters.me & filters.command("del", prefixes="."))
async def delete_messages(client, message: Message):
    try:
        count = int(message.command[1])
        is_saved = message.chat.id == (await client.get_me()).id
        async for msg in client.get_chat_history(message.chat.id, limit=count + 1):
            if msg.from_user and msg.from_user.is_self:
                # اگر در Saved Messages بود پیام اصلی دستور پاک نشه
                if is_saved and msg.id == message.id:
                    continue
                await msg.delete()
    except Exception:
        await message.edit_text("❌ مثال: `.del 5`")

@app.on_message(filters.me & filters.command("purge", prefixes="."))
async def purge_chat(client, message: Message):
    if not message.reply_to_message:
        await message.edit_text("❌ روی پیامی که می‌خواهید پاکسازی از آنجا شروع شود ریپلای کنید.")
        return
    start_id = message.reply_to_message.id
    end_id = message.id
    msg_ids = list(range(start_id, end_id + 1))
    await client.delete_messages(message.chat.id, msg_ids)

@app.on_message(filters.me & filters.command("info", prefixes="."))
async def get_info(client, message: Message):
    target = message.reply_to_message.from_user if message.reply_to_message else message.chat
    text = f"🆔 **آیدی:** `{target.id}`\n"
    if hasattr(target, 'first_name'):
        text += f"👤 **نام:** `{target.first_name}`\n"
    if hasattr(target, 'username') and target.username:
        text += f"🌐 **یوزرنیم:** @{target.username}\n"
    await message.edit_text(text)

# ==================== AUTOMATIONS (AFK, PMBOT, ANTI-DELETE, AUTO-DICE) ====================

@app.on_message(filters.private & ~filters.me)
async def handle_private(client, message: Message):
    # AFK Auto Reply
    if STATE["afk"]:
        await message.reply_text(f"🌙 **کاربر در حالت غیبت است.**\nدلیل: `{STATE['afk_reason']}`")
    # PM Bot Auto Reply
    elif STATE["pm_bot"]:
        await message.reply_text(STATE["pm_text"])

@app.on_deleted_messages()
async def anti_delete_handler(client, messages):
    if not STATE["anti_delete"]:
        return
    for msg in messages:
        if msg.text or msg.caption:
            log_text = f"🛡 **پیام پاک شده کشف شد!**\n👤 فرستنده آیدی: `{msg.from_user.id if msg.from_user else 'ناشناس'}`\n📝 متن: {msg.text or msg.caption}"
            me = await client.get_me()
            await client.send_message(me.id, log_text)

# ==================== MAIN EXECUTION ====================
async def main():
    print("🔄 Starting Pyrogram Client...")
    await app.start()
    
    me = await app.get_me()
    print(f"✅ Logged in successfully as: {me.first_name} (ID: {me.id})")
    
    STATE["original_name"] = re.sub(r'\s*\|?\s*[\d۰-۹⓿-❾𝟢-𝟫]+:[\d۰-۹⓿-❾𝟢-𝟫]+', '', me.first_name).strip()
    asyncio.create_task(background_tasks())
    
    print("🚀 Selfbot is ONLINE & Listening for commands!")
    await idle()
    await app.stop()

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
