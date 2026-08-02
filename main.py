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
    1: ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9"],
    2: ["۰", "۱", "۲", "۳", "۴", "۵", "۶", "۷", "۸", "۹"],
    3: ["⓿", "❶", "❷", "❸", "❹", "❺", "❻", "❼", "❽", "❾"],
    4: ["𝟢", "𝟣", "𝟤", "𝟥", "𝟦", "𝟧", "𝟨", "𝟩", "𝟪", "𝟫"]
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

🛠 **دستورات اصلی:**
• `.loop [ID/here] [ثانیه] [متن]` ➔ ارسال تکراری با گزارش دقیق
• `.rdice on [even/odd/1-6]` ➔ تاس هوشمند
• `.rslot on` ➔ اسلات هوشمند
• `.type [متن]` ➔ تایپ متحرک با سرعت بالا
• `.ping` ➔ بررسی پینگ سلف‌بات"""

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
    await reply.edit_text(f"⚡️ **سلف‌بات فعال است!**\nپینگ: `{ms:.1f}ms`")

# --- LOOP COMMAND ---
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
        
        # ارسال گزارش دقیق به Saved Messages
        await client.send_message("me", report_text)
        await message.delete()

    except Exception as e:
        await message.edit_text(f"❌ فرمت نادرست است.\nنمونه: `.loop here 246 متن پیام`\nخطا: `{e}`")

@app.on_message(filters.me & filters.command("stoploop", prefixes="."))
async def stop_loops(client, message: Message):
    for t in STATE["loops"].values():
        t.cancel()
    STATE["loops"].clear()
    await message.edit_text("🛑 **تمام ارسال‌های تکراری متوقف شدند.**")

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
    # تاس
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

    # اسلات
    elif STATE["rslot"] and message.dice.emoji == "🎰":
        if message.dice.value != 64:
            await message.delete()
            await client.send_dice(message.chat.id, emoji="🎰")

# --- FAST TYPEWRITER ---
@app.on_message(filters.me & filters.command("type", prefixes="."))
async def typewriter(client, message: Message):
    text = " ".join(message.command[1:])
    typed = ""
    for char in text:
        typed += char
        await message.edit_text(typed + "▒")
        await asyncio.sleep(0.02)
    await message.edit_text(typed)

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
