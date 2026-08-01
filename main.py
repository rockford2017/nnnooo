import asyncio
import os
import re
from datetime import datetime
from pytz import timezone
from pyrogram import Client, filters
from pyrogram.types import Message

# ==================== CONFIGURATION ====================
API_ID = int(os.getenv("API_ID", "6"))
API_HASH = os.getenv("API_HASH", "eb06d4abfb49dc3eeb1aeb98ae0f581e")
SESSION_STRING = os.getenv("SESSION_STRING", "")

if SESSION_STRING:
    app = Client("my_selfbot", api_id=API_ID, api_hash=API_HASH, session_string=SESSION_STRING)
else:
    app = Client("my_selfbot", api_id=API_ID, api_hash=API_HASH)

# ==================== STATE MANAGEMENT ====================
STATE = {
    "clock": False,
    "clock_style": 1,
    "original_name": "",
    "afk": False,
    "afk_reason": "",
    "antidelete": True,
    "sec_pv": False,
    "dice_active": False,
    "dice_target": None,
    "slot_active": True,
    "slot_target": 64,
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
    afk_status = "🟢 فعال" if STATE["afk"] else "🔴 خاموش"
    antidel_status = "🟢 فعال" if STATE["antidelete"] else "🔴 خاموش"
    sec_status = "🟢 فعال" if STATE["sec_pv"] else "🔴 خاموش"
    
    dice_st = "🔴 خاموش"
    if STATE["dice_active"]:
        dice_st = f"🟢 روشن (هدف: {STATE['dice_target']})"
        
    slot_st = "🔴 خاموش"
    if STATE["slot_active"]:
        slot_st = f"🟢 روشن (هدف: {STATE['slot_target']})"

    return f"""📋 **داشبورد سلف‌بات اختصاصی A**
━━━━━━━━━━━━━━━━━━━━
⏰ **ساعت اسم:** [ {clock_status} ]
🌙 **حالت AFK:** [ {afk_status} ]
🛡 **ضد پاکسازی:** [ {antidel_status} ]
🤖 **منشی پیوی:** [ {sec_status} ]
🎲 **تاس شانس:** [ {dice_st} ]
🎰 **اسلات شانس:** [ {slot_st} ]
━━━━━━━━━━━━━━━━━━━━

🛠 **لیست دستورات کامل:**

🎲🎰 **تاس و اسلات پیشرفته:**
• `.rdice on [even/odd/1-6]` ➔ روشن کردن تاس
• `.rdice off` ➔ خاموش کردن تاس
• `.rslot on` ➔ روشن کردن اسلات (۷۷۷)
• `.rslot off` ➔ خاموش کردن اسلات

⚡️ **مدیریت سیستم:**
• `.clock` ➔ روشن/خاموش کردن ساعت
• `.clockstyle [1-4]` ➔ تغییر استایل ساعت
• `.afk [دلیل]` / `.unafk` ➔ حالت غیبت

🔄 **زمان‌بندی و ارسال:**
• `.loop [ID] [ثانیه] [متن]` ➔ ارسال تکراری
• `.loops` ➔ لیست ارسال‌های فعال
• `.stoploop` ➔ توقف تمام ارسال‌ها
• `.schedule [ID] [HH:MM] [متن]` ➔ ارسال سر ساعت

🌐 **ابزارهای کاربردی:**
• `.mute` / `.unmute` ➔ مدیریت کاربر
• `.purge` ➔ پاکسازی پیام‌ها
• `.calc [عبارت]` ➔ ماشین حساب
• `.tags` ➔ مشاهده منشن‌ها
• `.save` ➔ ذخیره رسانه تایمردار
• `.type` ➔ تایپ متحرک
• `.sticker` ➔ ساخت استیکر

🛠 **ابزارهای عمومی:**
• `.del [تعداد]` ➔ پاکسازی پیام خودت
• `.info` ➔ اطلاعات چت/کاربر
• `.font [متن]` ➔ ساخت فونت
• `.ping` ➔ تست سرعت"""

# ==================== CLOCK TASK (OPTIMIZED) ====================
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
            await asyncio.sleep(15)  # چک کردن سریع هر ۱۵ ثانیه بدون لگ
        except Exception as e:
            print(f"Clock Error: {e}")
            await asyncio.sleep(20)

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
    await reply.edit_text(f"⚡️ **پینگ سلف‌بات:** `{ms:.1f}ms`")

@app.on_message(filters.me & filters.command("clock", prefixes="."))
async def toggle_clock(client, message: Message):
    STATE["clock"] = not STATE["clock"]
    if STATE["clock"]:
        await message.edit_text("⏰ **ساعت روی اسم روشن شد 🟢**")
    else:
        # برگرداندن اسم به حالت اول هنگام خاموش کردن
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
    except:
        await message.edit_text("❌ فرمت صحیح: `.clockstyle 1`")

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
        "text": message.text or message.caption or "رسانه / ایموجی",
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

    text += "━━━━━━━━━━━━━━━━━━━━\n💡 *برای پاکسازی از `.cleartags` استفاده کنید.*"
    await message.edit_text("✅ **لیست منشن‌ها به Saved Messages فرستاده شد.**")
    await client.send_message("me", text, disable_web_page_preview=True)

@app.on_message(filters.me & filters.command("cleartags", prefixes="."))
async def clear_tags(client, message: Message):
    STATE["tags"].clear()
    await message.edit_text("🧹 **لیست منشن‌ها پاکسازی شد.**")

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

@app.on_message(filters.me & filters.command("loops", prefixes="."))
async def list_loops(client, message: Message):
    if not STATE["loops"]:
        await message.edit_text("📭 هیچ حلقه ارسالی فعال نیست.")
        return
    await message.edit_text(f"🔄 **تعداد ارسال‌های فعال:** `{len(STATE['loops'])}`\nبرای توقف از `.stoploop` استفاده کنید.")

@app.on_message(filters.me & filters.command("stoploop", prefixes="."))
async def stop_loops(client, message: Message):
    for task in STATE["loops"].values():
        task.cancel()
    STATE["loops"].clear()
    await message.edit_text("🛑 **تمام ارسال‌های تکراری متوقف شدند.**")

@app.on_message(filters.me & filters.command("rdice", prefixes="."))
async def rdice_handler(client, message: Message):
    if len(message.command) < 2:
        await message.edit_text("❌ فرمت صحیح: `.rdice on [even/odd/1-6]` یا `.rdice off`")
        return
    
    sub = message.command[1].lower()
    if sub == "off":
        STATE["dice_active"] = False
        await message.edit_text("🎲 **تاس خودکار خاموش شد.**")
    elif sub == "on":
        target = message.command[2].lower() if len(message.command) > 2 else "even"
        STATE["dice_active"] = True
        STATE["dice_target"] = target
        await message.edit_text(f"🎲 **تاس خودکار روشن شد!**\nهدف: `{target}`")

@app.on_message(filters.me & filters.command("rslot", prefixes="."))
async def rslot_handler(client, message: Message):
    if len(message.command) < 2:
        await message.edit_text("❌ فرمت صحیح: `.rslot on` یا `.rslot off`")
        return
    
    sub = message.command[1].lower()
    if sub == "off":
        STATE["slot_active"] = False
        await message.edit_text("🎰 **اسلات خودکار خاموش شد.**")
    elif sub == "on":
        STATE["slot_active"] = True
        STATE["slot_target"] = 64
        await message.edit_text("🎰 **اسلات خودکار روشن شد!**")

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

@app.on_message(filters.me & filters.command("purge", prefixes="."))
async def purge_msgs(client, message: Message):
    if not message.reply_to_message:
        await message.edit_text("❌ روی پیام شروع پاکسازی ریپلای کنید.")
        return
    start_id = message.reply_to_message.id
    end_id = message.id
    msg_ids = list(range(start_id, end_id + 1))
    await client.delete_messages(message.chat.id, msg_ids)

# ==================== MAIN ====================
async def main():
    await app.start()
    
    # گرفتن و ذخیره اسم اصلی تو در بدو ورود
    me = await app.get_me()
    base_name = re.sub(r'\s*\|?\s*[\d۰-۹⓿-❾𝟢-𝟫]+:[\d۰-۹⓿-❾𝟢-𝟫]+', '', me.first_name).strip()
    STATE["original_name"] = base_name

    asyncio.create_task(clock_loop())
    print("✅ Selfbot Online & Fast!")
    await asyncio.Event().wait()

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
