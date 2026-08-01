import asyncio
import os
import re
import sys
from datetime import datetime
from pytz import timezone
from pyrogram import Client, filters
from pyrogram.types import Message

# ==================== CONFIGURATION ====================
API_ID = int(os.getenv("API_ID", "6"))
API_HASH = os.getenv("API_HASH", "eb06d4abfb49dc3eeb1aeb98ae0f581e")
SESSION_STRING = os.getenv("SESSION_STRING", "")

if not SESSION_STRING:
    print("❌ ERROR: SESSION_STRING environment variable is missing or empty!")
    sys.exit(1)

app = Client("my_selfbot", api_id=API_ID, api_hash=API_HASH, session_string=SESSION_STRING)

# ==================== STATE MANAGEMENT ====================
STATE = {
    "clock": False,
    "clock_style": 1,
    "original_name": "",
    "dice_active": False,
    "dice_target": "even",
    "slot_active": False,
    "loops": {},
    "tags": []
}

CLOCK_STYLES = {
    1: ["۰", "۱", "۲", "۳", "۴", "۵", "۶", "۷", "۸", "۹"],
    2: ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9"],
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

def get_dashboard_text():
    clock_status = f"🟢 فعال | استایل {STATE['clock_style']}" if STATE["clock"] else f"🔴 خاموش | استایل {STATE['clock_style']}"
    dice_st = f"🟢 روشن (هدف: {STATE['dice_target']})" if STATE["dice_active"] else "🔴 خاموش"
    slot_st = "🟢 روشن (هدف: ۷۷۷)" if STATE["slot_active"] else "🔴 خاموش"

    return f"""📋 **داشبورد سلف‌بات اختصاصی**
━━━━━━━━━━━━━━━━━━━━
⏰ **ساعت اسم:** [ {clock_status} ]
🎲 **تاس هوشمند:** [ {dice_st} ]
🎰 **اسلات هوشمند:** [ {slot_st} ]
📌 **منشن‌های ذخیره شده:** [ `{len(STATE['tags'])}` عدد ]
🔄 **حلقه‌های فعال ارسال:** [ `{len(STATE['loops'])}` عدد ]
━━━━━━━━━━━━━━━━━━━━

🛠 **دستورات سریع:**
• `.ping` ➔ بررسی وضعیت سلف‌بات
• `.clock` ➔ روشن/خاموش ساعت اسم
• `.clockstyle 1-4` ➔ تغییر استایل ساعت
• `.rdice on/off` ➔ کنترل تاس خودکار
• `.rslot on/off` ➔ کنترل اسلات خودکار
• `.loop [چت] [ثانیه] [متن]` ➔ ارسال تکراری
• `.del [تعداد]` ➔ پاکسازی پیام‌های شما
• `.calc [عبارت]` ➔ ماشین حساب"""

# ==================== CLOCK TASK ====================
async def clock_loop():
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
            await asyncio.sleep(20)
        except Exception as e:
            print(f"Clock Error: {e}")
            await asyncio.sleep(30)

# ==================== HANDLERS ====================

# استفاده از filters.me برای اجرا توسط خودت در همه چت‌ها (حتی Saved Messages)
@app.on_message(filters.me & filters.command(["panel", "help"], prefixes="."))
async def show_panel(client, message: Message):
    await message.edit_text(get_dashboard_text())

@app.on_message(filters.me & filters.command("ping", prefixes="."))
async def ping_handler(client, message: Message):
    start = datetime.now()
    reply = await message.edit_text("🚀 در حال بررسی...")
    end = datetime.now()
    ms = (end - start).microseconds / 1000
    await reply.edit_text(f"⚡️ **سلف‌بات فعال و آنلاین است!**\nپینگ: `{ms:.1f}ms`")

@app.on_message(filters.me & filters.command("clock", prefixes="."))
async def toggle_clock(client, message: Message):
    STATE["clock"] = not STATE["clock"]
    if STATE["clock"]:
        await message.edit_text("⏰ **ساعت روی اسم روشن شد 🟢**")
    else:
        try:
            if STATE["original_name"]:
                await app.update_profile(first_name=STATE["original_name"])
        except Exception:
            pass
        await message.edit_text("⏰ **ساعت روی اسم خاموش شد 🔴**")

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

# ----------------- TAG TRACKER -----------------
@app.on_message(filters.mentioned & ~filters.me)
async def mention_tracker(client, message: Message):
    if message.chat.username:
        msg_link = f"https://t.me/{message.chat.username}/{message.id}"
    else:
        chat_id_str = str(message.chat.id).replace("-100", "")
        msg_link = f"https://t.me/c/{chat_id_str}/{message.id}"

    sender_name = message.from_user.first_name if message.from_user else "ناشناس"
    chat_title = message.chat.title if message.chat.title else "چت"

    tag_data = {
        "link": msg_link,
        "sender": sender_name,
        "chat": chat_title,
        "text": message.text or message.caption or "رسانه",
        "time": datetime.now(timezone('Asia/Tehran')).strftime("%H:%M")
    }
    STATE["tags"].append(tag_data)

@app.on_message(filters.me & filters.command("tags", prefixes="."))
async def show_tags(client, message: Message):
    if not STATE["tags"]:
        await message.edit_text("📭 **هیچ منشنی ثبت نشده است.**")
        return

    text = "📌 **لیست آخرین منشن‌های شما:**\n━━━━━━━━━━━━━━━━━━━━\n"
    for idx, t in enumerate(STATE["tags"][-10:], 1):
        text += f"{idx}. 👥 **{t['chat']}** | 👤 {t['sender']} (`{t['time']}`)\n"
        text += f"   🔗 [رفتن به پیام]({t['link']})\n\n"

    await message.edit_text("✅ **لیست منشن‌ها به Saved Messages فرستاده شد.**")
    await client.send_message("me", text, disable_web_page_preview=True)

@app.on_message(filters.me & filters.command("cleartags", prefixes="."))
async def clear_tags(client, message: Message):
    STATE["tags"].clear()
    await message.edit_text("🧹 **لیست منشن‌ها پاکسازی شد.**")

# ----------------- LOOP ENGINE -----------------
@app.on_message(filters.me & filters.command("loop", prefixes="."))
async def start_loop(client, message: Message):
    try:
        args = message.command
        if len(args) < 4:
            await message.edit_text("❌ **فرمت اشتباه!**\nمثال: `.loop @username 10 سلام`")
            return

        target = args[1]
        seconds = int(args[2])
        text = " ".join(args[3:])

        async def loop_runner(t_chat, s_sec, m_text):
            while True:
                try:
                    await client.send_message(t_chat, m_text)
                except Exception as e:
                    print(f"Loop error: {e}")
                await asyncio.sleep(s_sec)

        task = asyncio.create_task(loop_runner(target, seconds, text))
        task_id = len(STATE["loops"]) + 1
        STATE["loops"][task_id] = task
        
        await message.edit_text(f"🔄 **ارسال تکراری فعال شد!**\n🎯 به: `{target}`\n⏱ هر `{seconds}` ثانیه")
    except Exception as e:
        await message.edit_text(f"❌ خطا: {e}")

@app.on_message(filters.me & filters.command("stoploop", prefixes="."))
async def stop_loops(client, message: Message):
    for task in STATE["loops"].values():
        task.cancel()
    STATE["loops"].clear()
    await message.edit_text("🛑 **تمام ارسال‌های تکراری متوقف شدند.**")

# ----------------- GAME ENGINE -----------------
@app.on_message(filters.me & filters.command("rdice", prefixes="."))
async def rdice_command(client, message: Message):
    if len(message.command) < 2:
        await message.edit_text("❌ **فرمت صحیح:**\n`.rdice on [even/odd/1-6]`\n`.rdice off`")
        return
    sub = message.command[1].lower()
    if sub == "on":
        STATE["dice_active"] = True
        STATE["dice_target"] = message.command[2].lower() if len(message.command) > 2 else "even"
        await message.edit_text(f"🎲 **تاس خودکار روشن شد!**\nهدف: `{STATE['dice_target']}`")
    else:
        STATE["dice_active"] = False
        await message.edit_text("🎲 **تاس خودکار خاموش شد.**")

@app.on_message(filters.me & filters.command("rslot", prefixes="."))
async def rslot_command(client, message: Message):
    if len(message.command) < 2:
        await message.edit_text("❌ **فرمت صحیح:**\n`.rslot on`\n`.rslot off`")
        return
    sub = message.command[1].lower()
    if sub == "on":
        STATE["slot_active"] = True
        await message.edit_text("🎰 **اسلات خودکار روشن شد!**")
    else:
        STATE["slot_active"] = False
        await message.edit_text("🎰 **اسلات خودکار خاموش شد.**")

@app.on_message(filters.me & filters.dice)
async def auto_game_trigger(client, message: Message):
    if message.dice.emoji == "🎲" and STATE["dice_active"]:
        val = message.dice.value
        target = STATE["dice_target"]
        hit = False
        if target == "even" and val % 2 == 0: hit = True
        elif target == "odd" and val % 2 != 0: hit = True
        elif str(target) == str(val): hit = True

        if not hit:
            await asyncio.sleep(2.5)
            if STATE["dice_active"]:
                await client.send_dice(message.chat.id, emoji="🎲")
        else:
            await client.send_message(message.chat.id, f"🎯 **تاس برنده شد! عدد:** `{val}`")
            STATE["dice_active"] = False

    elif message.dice.emoji == "🎰" and STATE["slot_active"]:
        val = message.dice.value
        if val != 64:
            await asyncio.sleep(2.5)
            if STATE["slot_active"]:
                await client.send_dice(message.chat.id, emoji="🎰")
        else:
            await client.send_message(message.chat.id, "🎉 **برنده جک‌پات (777) شدی!**")
            STATE["slot_active"] = False

# ----------------- UTILITIES -----------------
@app.on_message(filters.me & filters.command("del", prefixes="."))
async def delete_messages(client, message: Message):
    try:
        count = int(message.command[1])
        async for msg in client.get_chat_history(message.chat.id, limit=count + 1):
            if msg.from_user and msg.from_user.is_self:
                await msg.delete()
    except Exception:
        await message.edit_text("❌ مثال: `.del 5`")

@app.on_message(filters.me & filters.command("calc", prefixes="."))
async def calculator(client, message: Message):
    try:
        expr = " ".join(message.command[1:])
        result = eval(expr)
        await message.edit_text(f"🧮 **محاسبه:** `{expr}`\n✅ **نتیجه:** `{result}`")
    except Exception:
        await message.edit_text("❌ عبارت ریاضی نامعتبر است.")

# ==================== MAIN RUNNER ====================
async def main():
    print("🔄 Starting Pyrogram Client...")
    await app.start()
    me = await app.get_me()
    print(f"✅ Logged in as: {me.first_name}")
    
    STATE["original_name"] = re.sub(r'\s*\|?\s*[\d۰-۹⓿-❾𝟢-𝟫]+:[\d۰-۹⓿-❾𝟢-𝟫]+', '', me.first_name).strip()
    asyncio.create_task(clock_loop())
    
    print("🚀 Selfbot is ONLINE and Listening for commands...")
    await asyncio.Event().wait()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass
