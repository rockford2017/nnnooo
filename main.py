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
    "dice_active": False,
    "dice_target": "even", # even, odd, or 1-6
    "slot_active": False,
    "loops": {},
    "tags": {}
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

🛠 **دستورات کامل سلف‌بات:**
• `.ping` ➔ بررسی وضعیت و سرعت
• `.panel` ➔ نمایش همین پنل مدیریت
• `.clock` ➔ روشن/خاموش ساعت اسم
• `.clockstyle 1-4` ➔ تغییر استایل فونت ساعت
• `.dice [target]` ➔ پرتاب تاس (odd/even/1-6)
• `.slot` ➔ شانس اسلات (هدف 777)
• `.save [name]` ➔ ذخیره پیام ریپلای شده
• `.get [name]` ➔ فراخوانی پیام ذخیره شده
• `.tags` ➔ لیست پیام‌های ذخیره شده
• `.loop [cnt] [delay] [txt]` ➔ ارسال مکرر پیام
• `.stoploops` ➔ توقف همه حلقه‌ها
• `.del [cnt]` ➔ پاکسازی پیام‌های اخیر خودت
• `.calc [expr]` ➔ ماشین حساب ریاضی
• `.restart` ➔ ری‌استارت ربات"""

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
            await asyncio.sleep(25)
        except Exception:
            await asyncio.sleep(30)

# ==================== HANDLERS ====================

@app.on_message(filters.me & filters.command(["panel", "help"], prefixes="."))
async def show_panel(client, message: Message):
    await message.edit_text(get_dashboard_text())

@app.on_message(filters.me & filters.command("ping", prefixes="."))
async def ping_handler(client, message: Message):
    start = datetime.now()
    reply = await message.edit_text("🚀 در حال بررسی...")
    end = datetime.now()
    ms = (end - start).microseconds / 1000
    await reply.edit_text(f"⚡️ **سلف‌بات گیت‌هاب آنلاین است!**\nپینگ: `{ms:.1f}ms`")

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

# 🎲 DICE HANDLER
@app.on_message(filters.me & filters.command("dice", prefixes="."))
async def roll_dice_target(client, message: Message):
    target = message.command[1] if len(message.command) > 1 else "even"
    await message.delete()
    
    attempts = 0
    max_attempts = 15
    while attempts < max_attempts:
        msg = await client.send_dice(message.chat.id, emoji="🎲")
        val = msg.dice.value
        
        is_hit = False
        if target == "even" and val % 2 == 0:
            is_hit = True
        elif target == "odd" and val % 2 != 0:
            is_hit = True
        elif target.isdigit() and int(target) == val:
            is_hit = True
            
        if is_hit:
            break
        else:
            await msg.delete()
            attempts += 1
            await asyncio.sleep(0.3)

# 🎰 SLOT HANDLER
@app.on_message(filters.me & filters.command("slot", prefixes="."))
async def roll_slot_777(client, message: Message):
    await message.delete()
    attempts = 0
    max_attempts = 20
    while attempts < max_attempts:
        msg = await client.send_dice(message.chat.id, emoji="🎰")
        if msg.dice.value == 64:  # 64 is Jackpot (777) in Telegram Slot
            break
        else:
            await msg.delete()
            attempts += 1
            await asyncio.sleep(0.3)

# 📌 SAVE & GET TAGS
@app.on_message(filters.me & filters.command("save", prefixes="."))
async def save_tag(client, message: Message):
    if not message.reply_to_message:
        await message.edit_text("❌ لطفاً روی پیامی که می‌خواهید ذخیره شود ریپلای کنید.")
        return
    if len(message.command) < 2:
        await message.edit_text("❌ یک نام برای پیام تعیین کنید. مثال: `.save test`")
        return
    
    tag_name = message.command[1]
    STATE["tags"][tag_name] = message.reply_to_message.text or message.reply_to_message.caption or ""
    await message.edit_text(f"✅ پیام با نام `{tag_name}` ذخیره شد.")

@app.on_message(filters.me & filters.command("get", prefixes="."))
async def get_tag(client, message: Message):
    if len(message.command) < 2:
        await message.edit_text("❌ نام پیام را وارد کنید.")
        return
    tag_name = message.command[1]
    if tag_name in STATE["tags"]:
        await message.edit_text(STATE["tags"][tag_name])
    else:
        await message.edit_text("❌ پیامی با این نام یافت نشد.")

@app.on_message(filters.me & filters.command("tags", prefixes="."))
async def list_tags(client, message: Message):
    if not STATE["tags"]:
        await message.edit_text("📌 هیچ پیامی ذخیره نشده است.")
        return
    tags_list = "\n".join([f"• `{t}`" for t in STATE["tags"].keys()])
    await message.edit_text(f"📌 **پیام‌های ذخیره شده:**\n{tags_list}")

# 🔄 LOOP HANDLER
@app.on_message(filters.me & filters.command("loop", prefixes="."))
async def start_loop(client, message: Message):
    try:
        count = int(message.command[1])
        delay = int(message.command[2])
        text = " ".join(message.command[3:])
        await message.delete()
        
        async def loop_worker():
            for _ in range(count):
                await client.send_message(message.chat.id, text)
                await asyncio.sleep(delay)
                
        task = asyncio.create_task(loop_worker())
        STATE["loops"][len(STATE["loops"]) + 1] = task
    except Exception:
        await message.edit_text("❌ فرمت: `.loop [تعداد] [فاصله ثانیه] [متن]`")

@app.on_message(filters.me & filters.command("stoploops", prefixes="."))
async def stop_loops(client, message: Message):
    for t in STATE["loops"].values():
        t.cancel()
    STATE["loops"].clear()
    await message.edit_text("🛑 تمامی حلقه‌های ارسال متوقف شدند.")

# 🧹 DELETE & CALC
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
        await message.edit_text("❌ عبارت نامعتبر است.")

@app.on_message(filters.me & filters.command("restart", prefixes="."))
async def restart_bot(client, message: Message):
    await message.edit_text("🔄 **سلف‌بات در حال ری‌استارت است...**")
    os.execl(sys.executable, sys.executable, *sys.argv)

# ==================== MAIN EXECUTION ====================
async def main():
    print("🔄 Starting Pyrogram Client...")
    await app.start()
    
    me = await app.get_me()
    print(f"✅ Logged in successfully as: {me.first_name} (ID: {me.id})")
    
    STATE["original_name"] = re.sub(r'\s*\|?\s*[\d۰-۹⓿-❾𝟢-𝟫]+:[\d۰-۹⓿-❾𝟢-𝟫]+', '', me.first_name).strip()
    asyncio.create_task(clock_loop())
    
    print("🚀 Selfbot is ONLINE & Listening for commands!")
    
    await idle()
    await app.stop()

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
